"""
Withings API integration.

Withings uses OAuth2 for authentication and provides APIs for:
- Body measurements (weight, fat mass, muscle mass, etc.)
- Activity data (steps, distance, calories)
- Sleep data
- Blood pressure, heart rate

API docs: https://developer.withings.com/api-reference
"""
import logging
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from .base import BaseOAuthClient, OAuthConfig

logger = logging.getLogger(__name__)


class WithingsClient(BaseOAuthClient):
    PLATFORM = 'withings'

    def get_oauth_config(self):
        return OAuthConfig(
            platform_name='Withings',
            client_id=getattr(settings, 'WITHINGS_CLIENT_ID', ''),
            client_secret=getattr(settings, 'WITHINGS_CLIENT_SECRET', ''),
            authorize_url='https://account.withings.com/oauth2_user/authorize2',
            token_url='https://wbsapi.withings.net/v2/oauth2',
            api_base_url='https://wbsapi.withings.net',
            scopes=['user.info', 'user.metrics', 'user.activity', 'user.sleepevents'],
        )

    def exchange_code_for_token(self, code, redirect_uri):
        """Withings uses a custom token endpoint format."""
        config = self.get_oauth_config()
        data = {
            'action': 'requesttoken',
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': config.client_id,
            'client_secret': config.client_secret,
        }
        import requests
        response = requests.post(config.token_url, data=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        if result.get('status') != 0:
            raise ValueError(f"Withings token error: {result}")
        return result.get('body', {})

    def refresh_access_token(self, refresh_token):
        """Withings uses a custom refresh format."""
        config = self.get_oauth_config()
        data = {
            'action': 'requesttoken',
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': config.client_id,
            'client_secret': config.client_secret,
        }
        import requests
        response = requests.post(config.token_url, data=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        if result.get('status') != 0:
            raise ValueError(f"Withings refresh error: {result}")
        return result.get('body', {})

    def fetch_data(self, device, start_date, end_date):
        """Fetch body measurements from Withings."""
        from tracker.models import BodyComposition

        startdate = int(datetime.combine(start_date, datetime.min.time()).timestamp())
        enddate = int(datetime.combine(end_date, datetime.max.time()).timestamp())

        token = self.get_valid_token(device)
        import requests
        response = requests.post(
            'https://wbsapi.withings.net/measure',
            headers={'Authorization': f'Bearer {token}'},
            data={
                'action': 'getmeas',
                'startdate': startdate,
                'enddate': enddate,
                'meastypes': '1,6,8,76,77',  # weight, fat ratio, fat mass, muscle mass, bone mass
            },
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        if result.get('status') != 0:
            raise ValueError(f"Withings API error: {result}")

        measure_groups = result.get('body', {}).get('measuregrps', [])
        records = 0
        # Withings measure type mapping
        TYPE_MAP = {
            1: 'weight_kg',
            6: 'body_fat_percentage',
            8: 'fat_mass_kg',
            76: 'muscle_mass_kg',
            77: 'bone_mass_kg',
        }
        for grp in measure_groups:
            ts = grp.get('date', 0)
            meas_date = datetime.fromtimestamp(ts, tz=timezone.utc).date()
            values = {}
            for m in grp.get('measures', []):
                mtype = m.get('type')
                field = TYPE_MAP.get(mtype)
                if field:
                    value = m['value'] * (10 ** m['unit'])
                    values[field] = value

            if values:
                defaults = {}
                if 'weight_kg' in values:
                    defaults['weight_kg'] = values['weight_kg']
                if 'body_fat_percentage' in values:
                    defaults['body_fat_percentage'] = values['body_fat_percentage']
                if 'muscle_mass_kg' in values:
                    defaults['muscle_mass_kg'] = values['muscle_mass_kg']
                if 'bone_mass_kg' in values:
                    defaults['bone_density'] = values['bone_mass_kg']
                if defaults:
                    _, created = BodyComposition.objects.update_or_create(
                        date=meas_date,
                        defaults=defaults,
                    )
                    if created:
                        records += 1
        return records
