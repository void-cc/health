"""
Dexcom CGM API integration.

Dexcom uses OAuth2 for authentication and provides APIs for:
- Continuous glucose monitoring (CGM) data
- Estimated glucose values (EGVs)
- Calibrations
- Events

API docs: https://developer.dexcom.com/docs
"""
import logging
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from .base import BaseOAuthClient, OAuthConfig

logger = logging.getLogger(__name__)


class DexcomClient(BaseOAuthClient):
    PLATFORM = 'dexcom_cgm'

    def get_oauth_config(self):
        # Use sandbox URL if not in production
        base_url = getattr(settings, 'DEXCOM_BASE_URL', 'https://api.dexcom.com')
        return OAuthConfig(
            platform_name='Dexcom CGM',
            client_id=getattr(settings, 'DEXCOM_CLIENT_ID', ''),
            client_secret=getattr(settings, 'DEXCOM_CLIENT_SECRET', ''),
            authorize_url=f'{base_url}/v2/oauth2/login',
            token_url=f'{base_url}/v2/oauth2/token',
            api_base_url=f'{base_url}/v2/users/self',
            scopes=['offline_access'],
        )

    def fetch_data(self, device, start_date, end_date):
        """Fetch estimated glucose values from Dexcom."""
        from tracker.models import MetabolicLog

        records = 0
        start_str = datetime.combine(start_date, datetime.min.time()).strftime('%Y-%m-%dT%H:%M:%S')
        end_str = datetime.combine(end_date, datetime.max.time()).strftime('%Y-%m-%dT%H:%M:%S')

        try:
            egv_data = self.api_get(device, '/egvs', params={
                'startDate': start_str,
                'endDate': end_str,
            })
            daily_glucose = {}
            for record in egv_data.get('egvs', []):
                ts = record.get('systemTime', '')
                value = record.get('value')
                if ts and value:
                    reading_date = datetime.fromisoformat(ts.replace('Z', '+00:00')).date()
                    if reading_date not in daily_glucose:
                        daily_glucose[reading_date] = []
                    daily_glucose[reading_date].append(value)

            for reading_date, values in daily_glucose.items():
                avg_glucose = sum(values) / len(values)
                _, created = MetabolicLog.objects.update_or_create(
                    date=reading_date,
                    defaults={'blood_glucose': round(avg_glucose, 1)},
                )
                if created:
                    records += 1
        except Exception:
            logger.warning("Could not fetch EGVs from Dexcom", exc_info=True)

        return records
