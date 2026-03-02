"""
Samsung Health API integration.

Samsung Health uses OAuth2-based authorization through the Samsung Health
Data Store API. It provides access to:
- Steps, exercise
- Heart rate
- Sleep data
- Blood pressure, blood oxygen

Note: Samsung Health's API is primarily available through the Samsung Health
SDK and Samsung Health partner program. This client implements the REST API
approach available through the Samsung Health data store.

API docs: https://developer.samsung.com/health
"""
import logging
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from .base import BaseOAuthClient, OAuthConfig

logger = logging.getLogger(__name__)


class SamsungHealthClient(BaseOAuthClient):
    PLATFORM = 'samsung_health'

    def get_oauth_config(self):
        return OAuthConfig(
            platform_name='Samsung Health',
            client_id=getattr(settings, 'SAMSUNG_HEALTH_CLIENT_ID', ''),
            client_secret=getattr(settings, 'SAMSUNG_HEALTH_CLIENT_SECRET', ''),
            authorize_url='https://account.samsung.com/accounts/v1/OAUTH/authorize',
            token_url='https://account.samsung.com/accounts/v1/OAUTH/token',
            api_base_url='https://api.samsunghealth.com/v1',
            scopes=['health.heart_rate.read', 'health.sleep.read', 'health.body.read'],
        )

    def fetch_data(self, device, start_date, end_date):
        """Fetch health data from Samsung Health."""
        from tracker.models import VitalSign, SleepLog

        records = 0
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        # Fetch heart rate
        try:
            hr_data = self.api_get(device, '/heart-rate', params={
                'startDate': start_str,
                'endDate': end_str,
            })
            for entry in hr_data.get('data', []):
                entry_date = datetime.strptime(entry['date'], '%Y-%m-%d').date()
                hr = entry.get('restingHeartRate') or entry.get('avgHeartRate')
                if hr:
                    _, created = VitalSign.objects.update_or_create(
                        date=entry_date,
                        defaults={'heart_rate': int(hr)},
                    )
                    if created:
                        records += 1
        except Exception:
            logger.warning("Could not fetch heart rate from Samsung Health", exc_info=True)

        # Fetch sleep data
        try:
            sleep_data = self.api_get(device, '/sleep', params={
                'startDate': start_str,
                'endDate': end_str,
            })
            for entry in sleep_data.get('data', []):
                sleep_date = datetime.strptime(entry['date'], '%Y-%m-%d').date()
                defaults = {}
                if entry.get('totalSleepMinutes'):
                    defaults['total_sleep_minutes'] = entry['totalSleepMinutes']
                if entry.get('deepSleepMinutes'):
                    defaults['deep_sleep_minutes'] = entry['deepSleepMinutes']
                if entry.get('remSleepMinutes'):
                    defaults['rem_minutes'] = entry['remSleepMinutes']
                if defaults:
                    _, created = SleepLog.objects.update_or_create(
                        date=sleep_date,
                        defaults=defaults,
                    )
                    if created:
                        records += 1
        except Exception:
            logger.warning("Could not fetch sleep from Samsung Health", exc_info=True)

        return records
