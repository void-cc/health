"""
Fitbit API integration.

Fitbit uses OAuth2 for authentication and provides APIs for:
- Activity data (steps, distance, calories, active minutes)
- Heart rate (resting and intraday)
- Sleep data
- Body measurements (weight, BMI, body fat)

API docs: https://dev.fitbit.com/build/reference/web-api/
"""
import logging
from datetime import datetime

from django.conf import settings

from .base import BaseOAuthClient, OAuthConfig

logger = logging.getLogger(__name__)


class FitbitClient(BaseOAuthClient):
    PLATFORM = 'fitbit'

    def get_oauth_config(self):
        return OAuthConfig(
            platform_name='Fitbit',
            client_id=getattr(settings, 'FITBIT_CLIENT_ID', ''),
            client_secret=getattr(settings, 'FITBIT_CLIENT_SECRET', ''),
            authorize_url='https://www.fitbit.com/oauth2/authorize',
            token_url='https://api.fitbit.com/oauth2/token',
            api_base_url='https://api.fitbit.com',
            scopes=['activity', 'heartrate', 'sleep', 'weight', 'profile'],
        )

    def exchange_code_for_token(self, code, redirect_uri):
        """Fitbit requires Basic auth header for token exchange."""
        import base64
        config = self.get_oauth_config()
        credentials = base64.b64encode(
            f'{config.client_id}:{config.client_secret}'.encode()
        ).decode()
        import requests
        response = requests.post(
            config.token_url,
            headers={
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': redirect_uri,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def refresh_access_token(self, refresh_token):
        """Fitbit requires Basic auth header for token refresh."""
        import base64
        config = self.get_oauth_config()
        credentials = base64.b64encode(
            f'{config.client_id}:{config.client_secret}'.encode()
        ).decode()
        import requests
        response = requests.post(
            config.token_url,
            headers={
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def fetch_data(self, device, start_date, end_date):
        """Fetch heart rate and body data from Fitbit."""
        from tracker.models import VitalSign, BodyComposition, SleepLog

        records = 0
        date_str = end_date.strftime('%Y-%m-%d')
        start_str = start_date.strftime('%Y-%m-%d')

        # Fetch resting heart rate
        try:
            hr_data = self.api_get(
                device,
                f'/1/user/-/activities/heart/date/{start_str}/{date_str}.json',
            )
            for day in hr_data.get('activities-heart', []):
                day_date = datetime.strptime(day['dateTime'], '%Y-%m-%d').date()
                resting_hr = day.get('value', {}).get('restingHeartRate')
                if resting_hr:
                    _, created = VitalSign.objects.update_or_create(
                        date=day_date,
                        defaults={'heart_rate': resting_hr},
                    )
                    if created:
                        records += 1
        except Exception:
            logger.warning("Could not fetch heart rate from Fitbit", exc_info=True)

        # Fetch body weight
        try:
            body_data = self.api_get(
                device,
                f'/1/user/-/body/log/weight/date/{start_str}/{date_str}.json',
            )
            for entry in body_data.get('weight', []):
                entry_date = datetime.strptime(entry['date'], '%Y-%m-%d').date()
                # Store weight in VitalSign
                if entry.get('weight'):
                    VitalSign.objects.update_or_create(
                        date=entry_date,
                        defaults={'weight': entry['weight']},
                    )
                # Store body fat in BodyComposition
                if entry.get('fat'):
                    _, created = BodyComposition.objects.update_or_create(
                        date=entry_date,
                        defaults={'body_fat_percentage': entry['fat']},
                    )
                    if created:
                        records += 1
        except Exception:
            logger.warning("Could not fetch body data from Fitbit", exc_info=True)

        # Fetch sleep data
        try:
            sleep_data = self.api_get(
                device,
                f'/1.2/user/-/sleep/date/{start_str}/{date_str}.json',
            )
            for entry in sleep_data.get('sleep', []):
                sleep_date = datetime.strptime(entry['dateOfSleep'], '%Y-%m-%d').date()
                defaults = {
                    'total_sleep_minutes': entry.get('minutesAsleep'),
                }
                summary = entry.get('levels', {}).get('summary', {})
                if summary.get('deep', {}).get('minutes'):
                    defaults['deep_sleep_minutes'] = summary['deep']['minutes']
                if summary.get('rem', {}).get('minutes'):
                    defaults['rem_minutes'] = summary['rem']['minutes']
                if summary.get('light', {}).get('minutes'):
                    defaults['light_sleep_minutes'] = summary['light']['minutes']
                _, created = SleepLog.objects.update_or_create(
                    date=sleep_date,
                    defaults=defaults,
                )
                if created:
                    records += 1
        except Exception:
            logger.warning("Could not fetch sleep data from Fitbit", exc_info=True)

        return records
