"""
Garmin Connect API integration.

Garmin uses OAuth 1.0a for authentication and provides APIs for:
- Daily summaries (steps, distance, calories)
- Heart rate data
- Sleep data
- Body composition
- Activities

Note: Garmin's Health API uses OAuth 1.0a, which is different from OAuth 2.0
used by most other platforms. The push-based API requires a developer program
enrollment, so this client uses the pull-based approach via OAuth 1.0a.

API docs: https://developer.garmin.com/gc-developer-program/
"""
import logging
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from .base import BaseOAuthClient, OAuthConfig

logger = logging.getLogger(__name__)


class GarminClient(BaseOAuthClient):
    PLATFORM = 'garmin'

    def get_oauth_config(self):
        return OAuthConfig(
            platform_name='Garmin Connect',
            client_id=getattr(settings, 'GARMIN_CLIENT_ID', ''),
            client_secret=getattr(settings, 'GARMIN_CLIENT_SECRET', ''),
            authorize_url='https://connect.garmin.com/oauthConfirm',
            token_url='https://connectapi.garmin.com/oauth-service/oauth/access_token',
            api_base_url='https://apis.garmin.com/wellness-api/rest',
            scopes=[],
        )

    def get_authorization_url(self, redirect_uri, state=None):
        """
        Garmin uses OAuth 1.0a. This returns the authorization URL after
        obtaining a request token. The request token and secret are returned
        as part of a tuple: (auth_url, request_token, request_token_secret).
        The caller must store these for the callback exchange.
        """
        from requests_oauthlib import OAuth1Session
        config = self.get_oauth_config()

        request_token_url = 'https://connectapi.garmin.com/oauth-service/oauth/request_token'
        oauth = OAuth1Session(config.client_id, client_secret=config.client_secret,
                              callback_uri=redirect_uri)
        fetch_response = oauth.fetch_request_token(request_token_url)

        request_token = fetch_response.get('oauth_token', '')
        request_token_secret = fetch_response.get('oauth_token_secret', '')

        auth_url = oauth.authorization_url(config.authorize_url)
        # Store tokens on instance for the view to retrieve and persist in session
        self._request_token = request_token
        self._request_token_secret = request_token_secret
        return auth_url

    def exchange_code_for_token(self, code, redirect_uri,
                                request_token='', request_token_secret=''):
        """Garmin OAuth 1.0a token exchange using verifier."""
        from requests_oauthlib import OAuth1Session
        config = self.get_oauth_config()

        if not request_token or not request_token_secret:
            raise ValueError("Garmin OAuth 1.0a requires request_token and "
                             "request_token_secret for token exchange.")

        oauth = OAuth1Session(
            config.client_id,
            client_secret=config.client_secret,
            resource_owner_key=request_token,
            resource_owner_secret=request_token_secret,
            verifier=code,
        )
        token_response = oauth.fetch_access_token(config.token_url)
        return {
            'access_token': token_response.get('oauth_token', ''),
            'refresh_token': token_response.get('oauth_token_secret', ''),
        }

    def fetch_data(self, device, start_date, end_date):
        """Fetch daily summaries from Garmin."""
        from tracker.models import VitalSign, SleepLog
        from requests_oauthlib import OAuth1Session

        config = self.get_oauth_config()
        records = 0

        oauth = OAuth1Session(
            config.client_id,
            client_secret=config.client_secret,
            resource_owner_key=device.access_token,
            resource_owner_secret=device.refresh_token,
        )

        # Fetch daily summaries
        try:
            params = {
                'uploadStartTimeInSeconds': int(
                    datetime.combine(start_date, datetime.min.time()).timestamp()
                ),
                'uploadEndTimeInSeconds': int(
                    datetime.combine(end_date, datetime.max.time()).timestamp()
                ),
            }
            response = oauth.get(
                f'{config.api_base_url}/dailies',
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            for summary in response.json():
                cal_date = datetime.fromtimestamp(
                    summary.get('startTimeInSeconds', 0), tz=timezone.utc
                ).date()
                hr = summary.get('restingHeartRateInBeatsPerMinute')
                if hr:
                    _, created = VitalSign.objects.update_or_create(
                        date=cal_date,
                        defaults={'heart_rate': hr},
                    )
                    if created:
                        records += 1
        except Exception:
            logger.warning("Could not fetch dailies from Garmin", exc_info=True)

        # Fetch sleep data
        try:
            response = oauth.get(
                f'{config.api_base_url}/sleeps',
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            for entry in response.json():
                sleep_date = datetime.fromtimestamp(
                    entry.get('startTimeInSeconds', 0), tz=timezone.utc
                ).date()
                defaults = {}
                duration_s = entry.get('durationInSeconds')
                if duration_s:
                    defaults['total_sleep_minutes'] = duration_s // 60
                deep_s = entry.get('deepSleepDurationInSeconds')
                if deep_s:
                    defaults['deep_sleep_minutes'] = deep_s // 60
                rem_s = entry.get('remSleepDurationInSeconds')
                if rem_s:
                    defaults['rem_minutes'] = rem_s // 60
                light_s = entry.get('lightSleepDurationInSeconds')
                if light_s:
                    defaults['light_sleep_minutes'] = light_s // 60
                if defaults:
                    _, created = SleepLog.objects.update_or_create(
                        date=sleep_date,
                        defaults=defaults,
                    )
                    if created:
                        records += 1
        except Exception:
            logger.warning("Could not fetch sleep from Garmin", exc_info=True)

        return records
