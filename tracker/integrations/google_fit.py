"""
Google Fit API integration.

Google Fit uses OAuth2 for authentication and provides APIs for:
- Activity data (steps, distance, calories)
- Heart rate
- Body measurements (weight, height, body fat)
- Sleep sessions

API docs: https://developers.google.com/fit/rest
"""
import logging
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from .base import BaseOAuthClient, OAuthConfig

logger = logging.getLogger(__name__)


class GoogleFitClient(BaseOAuthClient):
    PLATFORM = 'google_fit'

    def get_oauth_config(self):
        return OAuthConfig(
            platform_name='Google Fit',
            client_id=getattr(settings, 'GOOGLE_FIT_CLIENT_ID', ''),
            client_secret=getattr(settings, 'GOOGLE_FIT_CLIENT_SECRET', ''),
            authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
            token_url='https://oauth2.googleapis.com/token',
            api_base_url='https://www.googleapis.com/fitness/v1/users/me',
            scopes=[
                'https://www.googleapis.com/auth/fitness.activity.read',
                'https://www.googleapis.com/auth/fitness.body.read',
                'https://www.googleapis.com/auth/fitness.heart_rate.read',
                'https://www.googleapis.com/auth/fitness.sleep.read',
            ],
        )

    def get_authorization_url(self, redirect_uri, state=None):
        """Google requires access_type=offline for refresh tokens."""
        from urllib.parse import urlencode
        config = self.get_oauth_config()
        params = {
            'response_type': 'code',
            'client_id': config.client_id,
            'redirect_uri': redirect_uri,
            'scope': ' '.join(config.scopes),
            'access_type': 'offline',
            'prompt': 'consent',
        }
        if state:
            params['state'] = state
        return f"{config.authorize_url}?{urlencode(params)}"

    def fetch_data(self, device, start_date, end_date):
        """Fetch activity and body data from Google Fit."""
        from tracker.models import VitalSign

        start_ns = int(datetime.combine(start_date, datetime.min.time()).timestamp() * 1e9)
        end_ns = int(datetime.combine(end_date, datetime.max.time()).timestamp() * 1e9)

        records = 0

        # Fetch heart rate data
        try:
            hr_data = self.api_get(device, '/dataSources/'
                'derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm'
                f'/datasets/{start_ns}-{end_ns}')
            for point in hr_data.get('point', []):
                values = point.get('value', [])
                if values:
                    hr_bpm = values[0].get('fpVal')
                    start_time_ns = int(point.get('startTimeNanos', 0))
                    point_date = datetime.fromtimestamp(
                        start_time_ns / 1e9, tz=timezone.utc
                    ).date()
                    if hr_bpm:
                        _, created = VitalSign.objects.update_or_create(
                            date=point_date,
                            defaults={'heart_rate': int(hr_bpm)},
                        )
                        if created:
                            records += 1
        except Exception:
            logger.warning("Could not fetch heart rate from Google Fit", exc_info=True)

        # Fetch body weight
        try:
            weight_data = self.api_get(device, '/dataSources/'
                'derived:com.google.weight:com.google.android.gms:merge_weight'
                f'/datasets/{start_ns}-{end_ns}')
            for point in weight_data.get('point', []):
                values = point.get('value', [])
                if values:
                    weight = values[0].get('fpVal')
                    start_time_ns = int(point.get('startTimeNanos', 0))
                    point_date = datetime.fromtimestamp(
                        start_time_ns / 1e9, tz=timezone.utc
                    ).date()
                    if weight:
                        _, created = VitalSign.objects.update_or_create(
                            date=point_date,
                            defaults={'weight': weight},
                        )
                        if created:
                            records += 1
        except Exception:
            logger.warning("Could not fetch weight from Google Fit", exc_info=True)

        return records
