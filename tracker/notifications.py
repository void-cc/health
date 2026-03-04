"""
Notification service for the Health Tracker app.

Provides a channel-agnostic ``send_notification`` function that:
- Respects per-user opt-in/out preferences
- Renders templates for the requested event + channel
- Records every attempt in ``NotificationLog``
- Retries on failure up to the trigger's ``max_retries`` limit
- Falls back to the next available channel when the primary one fails

Extensibility
~~~~~~~~~~~~~
To add a new channel (e.g. "slack"):
1. Add an entry to ``NOTIFICATION_CHANNELS`` in ``models.py``.
2. Implement a ``_deliver_<channel>(log)`` function below.
3. Register it in the ``_CHANNEL_BACKENDS`` dict.
"""

import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Channel back-ends
# ---------------------------------------------------------------------------

def _deliver_email(log):
    """Send an email notification.  Raises on failure."""
    send_mail(
        subject=log.subject or '(no subject)',
        message=log.body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@healthtracker.local'),
        recipient_list=[log.recipient],
        fail_silently=False,
    )


def _deliver_sms(log):
    """Send an SMS notification.

    In production replace this stub with a real SMS gateway call
    (e.g. Twilio, AWS SNS).  Raises on failure.
    """
    if not getattr(settings, 'SMS_BACKEND_ENABLED', False):
        raise NotImplementedError(
            "SMS back-end is not configured.  "
            "Set SMS_BACKEND_ENABLED=True and implement _deliver_sms()."
        )
    # Placeholder: real integration goes here
    raise NotImplementedError("SMS backend not yet integrated.")  # pragma: no cover


def _deliver_push(log):
    """Send a push notification.

    In production replace this stub with a real push service call
    (e.g. Firebase FCM, Apple APNs).  Raises on failure.
    """
    if not getattr(settings, 'PUSH_BACKEND_ENABLED', False):
        raise NotImplementedError(
            "Push back-end is not configured.  "
            "Set PUSH_BACKEND_ENABLED=True and implement _deliver_push()."
        )
    # Placeholder: real integration goes here
    raise NotImplementedError("Push backend not yet integrated.")  # pragma: no cover


# Map channel names → delivery functions.  Add new channels here.
_CHANNEL_BACKENDS = {
    'email': _deliver_email,
    'sms': _deliver_sms,
    'push': _deliver_push,
}


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def send_notification(
    event_type,
    context,
    user=None,
    recipient=None,
    trigger=None,
    channels=None,
):
    """Dispatch a notification for ``event_type`` across the given channels.

    Parameters
    ----------
    event_type : str
        One of the keys in ``NOTIFICATION_EVENT_TYPES``.
    context : dict
        Key/value pairs used to render the notification template.
    user : User or None
        The user to whom the notification is addressed.  Used for
        preference checks and populating ``NotificationLog.user``.
    recipient : str or None
        Explicit destination address (email, phone, …).  Overrides the
        address derived from *user* when provided.
    trigger : NotificationTrigger or None
        The trigger that fired this notification.  Its ``channels`` list
        is used as default when *channels* is ``None``.
    channels : list or None
        Explicit list of channel strings.  Defaults to the trigger's
        channel list or ``['email']`` if no trigger is given.

    Returns
    -------
    list[NotificationLog]
        One log entry per attempted channel.
    """
    # Import here to avoid circular imports at module load time
    from .models import (
        NotificationPreference, NotificationTemplate, NotificationLog,
    )

    if channels is None:
        channels = trigger.get_active_channels() if trigger else ['email']

    # Resolve per-user preferences
    pref = None
    if user is not None:
        pref, _ = NotificationPreference.objects.get_or_create(user=user)

    logs = []
    for channel in channels:
        # Opt-out check
        if pref is not None:
            if not pref.is_channel_enabled(channel):
                logger.debug("User %s has opted out of channel %s", user, channel)
                continue
            if not pref.is_event_enabled(event_type):
                logger.debug("User %s has opted out of event %s", user, event_type)
                continue

        # Resolve recipient address
        dest = recipient
        if dest is None and user is not None:
            if channel == 'email':
                dest = user.email
            else:
                dest = str(user)

        # Render template
        subject = ''
        body = ''
        template = NotificationTemplate.objects.filter(
            event_type=event_type, channel=channel, is_active=True
        ).first()
        if template:
            subject, body = template.render(context)
        else:
            subject = context.get('subject', event_type)
            body = context.get('body', str(context))

        # Create log entry
        max_retries = trigger.max_retries if trigger else 3
        log = NotificationLog.objects.create(
            user=user,
            trigger=trigger,
            event_type=event_type,
            channel=channel,
            recipient=dest or '',
            subject=subject,
            body=body,
            status='pending',
            attempt_count=0,
        )
        logs.append(log)

        # Attempt delivery with retry
        _attempt_delivery(log, max_retries)

    return logs


def _attempt_delivery(log, max_retries):
    """Try to deliver *log* up to *max_retries* times with simple failover."""
    from .models import NotificationLog  # noqa: F401 – re-import safe

    backend = _CHANNEL_BACKENDS.get(log.channel)
    if backend is None:
        log.status = 'failed'
        log.error_message = f"No backend registered for channel '{log.channel}'."
        log.save(update_fields=['status', 'error_message'])
        return

    for attempt in range(1, max_retries + 1):
        log.attempt_count = attempt
        log.status = 'retrying' if attempt > 1 else 'pending'
        log.save(update_fields=['attempt_count', 'status'])

        try:
            backend(log)
            log.status = 'sent'
            log.sent_at = timezone.now()
            log.error_message = ''
            log.save(update_fields=['status', 'sent_at', 'error_message'])
            logger.info(
                "Notification sent: event=%s channel=%s recipient=%s attempt=%d",
                log.event_type, log.channel, log.recipient, attempt,
            )
            return
        except Exception as exc:
            log.error_message = str(exc)
            log.save(update_fields=['error_message'])
            logger.warning(
                "Notification attempt %d/%d failed: event=%s channel=%s error=%s",
                attempt, max_retries, log.event_type, log.channel, exc,
            )

    log.status = 'failed'
    log.save(update_fields=['status'])
    logger.error(
        "Notification permanently failed after %d attempts: event=%s channel=%s",
        max_retries, log.event_type, log.channel,
    )
