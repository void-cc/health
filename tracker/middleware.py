from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone, translation
from django.contrib.auth import logout

from .models import UserSession


class SessionActivityMiddleware:
    """Middleware to track session activity and enforce inactivity timeouts."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request, 'session'):
            now = timezone.now()
            last_activity = request.session.get('last_activity')

            if last_activity:
                from datetime import datetime
                try:
                    last_activity_time = datetime.fromisoformat(last_activity)
                    if timezone.is_naive(last_activity_time):
                        last_activity_time = timezone.make_aware(last_activity_time)
                    inactivity_timeout = getattr(settings, 'SESSION_INACTIVITY_TIMEOUT', 1800)
                    elapsed = (now - last_activity_time).total_seconds()
                    if elapsed > inactivity_timeout:
                        # Mark session as inactive
                        session_key = request.session.session_key
                        if session_key:
                            UserSession.objects.filter(
                                session_key=session_key
                            ).update(is_active=False)
                        logout(request)
                        return redirect(settings.LOGIN_URL + '?timeout=1')
                except (ValueError, TypeError):
                    pass

            request.session['last_activity'] = now.isoformat()

            # Update UserSession last_activity
            session_key = request.session.session_key
            if session_key:
                UserSession.objects.filter(
                    session_key=session_key,
                    is_active=True
                ).update(last_activity=now)

        response = self.get_response(request)
        return response


class LanguagePreferenceMiddleware:
    """Activate the language stored in the authenticated user's profile.

    This middleware runs after ``LocaleMiddleware`` so that a user's explicit
    preference takes priority over the Accept-Language header or the session
    language set by Django's ``set_language`` view.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                language = request.user.profile.language
                if language:
                    translation.activate(language)
                    request.LANGUAGE_CODE = language
            except AttributeError:
                # User has no profile yet; fall back to default language detection
                pass

        response = self.get_response(request)
        return response
