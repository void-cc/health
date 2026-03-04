"""
Strava API integration.

Strava uses OAuth2 for authentication and provides APIs for:
- Activities (running, cycling, swimming, etc.)
- Heart rate data (from connected devices)
- Performance metrics

API docs: https://developers.strava.com/docs/reference/
"""
import logging
from datetime import datetime

from django.conf import settings

from .base import BaseOAuthClient, OAuthConfig

logger = logging.getLogger(__name__)


class StravaClient(BaseOAuthClient):
    PLATFORM = 'strava'

    def get_oauth_config(self):
        return OAuthConfig(
            platform_name='Strava',
            client_id=getattr(settings, 'STRAVA_CLIENT_ID', ''),
            client_secret=getattr(settings, 'STRAVA_CLIENT_SECRET', ''),
            authorize_url='https://www.strava.com/oauth/authorize',
            token_url='https://www.strava.com/oauth/token',
            api_base_url='https://www.strava.com/api/v3',
            scopes=['activity:read_all'],
        )

    def fetch_data(self, device, start_date, end_date):
        """Fetch activity data from Strava."""
        from tracker.models import VitalSign

        records = 0
        after_ts = int(datetime.combine(start_date, datetime.min.time()).timestamp())
        before_ts = int(datetime.combine(end_date, datetime.max.time()).timestamp())

        try:
            activities = self.api_get(device, '/athlete/activities', params={
                'after': after_ts,
                'before': before_ts,
                'per_page': 100,
            })
            for activity in activities:
                if activity.get('has_heartrate') and activity.get('average_heartrate'):
                    start_date_str = activity.get('start_date', '')
                    if start_date_str:
                        activity_date = datetime.fromisoformat(
                            start_date_str.replace('Z', '+00:00')
                        ).date()
                        _, created = VitalSign.objects.update_or_create(
                            date=activity_date,
                            defaults={
                                'heart_rate': int(activity['average_heartrate']),
                            },
                        )
                        if created:
                            records += 1
        except Exception:
            logger.warning("Could not fetch activities from Strava", exc_info=True)

        return records
