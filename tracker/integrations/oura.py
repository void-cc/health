"""
Oura Ring API integration.

Oura uses OAuth2 for authentication and provides APIs for:
- Sleep data (duration, stages, efficiency)
- Activity data (steps, calories, movement)
- Readiness scores
- Heart rate

API docs: https://cloud.ouraring.com/v2/docs
"""
import logging
from datetime import datetime

from django.conf import settings

from .base import BaseOAuthClient, OAuthConfig

logger = logging.getLogger(__name__)


class OuraClient(BaseOAuthClient):
    PLATFORM = 'oura'

    def get_oauth_config(self):
        return OAuthConfig(
            platform_name='Oura Ring',
            client_id=getattr(settings, 'OURA_CLIENT_ID', ''),
            client_secret=getattr(settings, 'OURA_CLIENT_SECRET', ''),
            authorize_url='https://cloud.ouraring.com/oauth/authorize',
            token_url='https://api.ouraring.com/oauth/token',
            api_base_url='https://api.ouraring.com/v2/usercollection',
            scopes=['daily', 'heartrate', 'personal', 'session', 'sleep'],
        )

    def fetch_data(self, device, start_date, end_date):
        """Fetch sleep and heart rate data from Oura."""
        from tracker.models import SleepLog, VitalSign

        records = 0
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        # Fetch sleep data
        try:
            sleep_data = self.api_get(device, '/sleep', params={
                'start_date': start_str,
                'end_date': end_str,
            })
            for entry in sleep_data.get('data', []):
                sleep_date = datetime.strptime(entry['day'], '%Y-%m-%d').date()
                defaults = {}
                if entry.get('total_sleep_duration'):
                    defaults['total_sleep_minutes'] = entry['total_sleep_duration'] // 60
                if entry.get('deep_sleep_duration'):
                    defaults['deep_sleep_minutes'] = entry['deep_sleep_duration'] // 60
                if entry.get('rem_sleep_duration'):
                    defaults['rem_minutes'] = entry['rem_sleep_duration'] // 60
                if entry.get('light_sleep_duration'):
                    defaults['light_sleep_minutes'] = entry['light_sleep_duration'] // 60
                if entry.get('awake_time'):
                    defaults['awake_minutes'] = entry['awake_time'] // 60
                if defaults:
                    _, created = SleepLog.objects.update_or_create(
                        date=sleep_date,
                        defaults=defaults,
                    )
                    if created:
                        records += 1
        except Exception:
            logger.warning("Could not fetch sleep data from Oura", exc_info=True)

        # Fetch heart rate
        try:
            hr_data = self.api_get(device, '/heartrate', params={
                'start_date': start_str,
                'end_date': end_str,
            })
            daily_hr = {}
            for entry in hr_data.get('data', []):
                ts = entry.get('timestamp', '')
                if ts:
                    point_date = datetime.fromisoformat(ts.replace('Z', '+00:00')).date()
                    bpm = entry.get('bpm')
                    if bpm and (point_date not in daily_hr):
                        daily_hr[point_date] = bpm

            for point_date, bpm in daily_hr.items():
                _, created = VitalSign.objects.update_or_create(
                    date=point_date,
                    defaults={'heart_rate': bpm},
                )
                if created:
                    records += 1
        except Exception:
            logger.warning("Could not fetch heart rate from Oura", exc_info=True)

        return records
