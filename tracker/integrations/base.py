"""
Base OAuth2 integration client for wearable health platforms.
"""
import logging
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)


class OAuthConfig:
    """Configuration for an OAuth2 platform integration."""

    def __init__(self, platform_name, client_id, client_secret,
                 authorize_url, token_url, api_base_url, scopes=None):
        self.platform_name = platform_name
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.api_base_url = api_base_url
        self.scopes = scopes or []


class BaseOAuthClient:
    """
    Base class for OAuth2 health platform integrations.

    Subclasses must define:
        - PLATFORM: str matching WEARABLE_PLATFORMS key
        - get_oauth_config(): returns OAuthConfig
        - fetch_data(device, start_date, end_date): fetches and stores data
    """

    PLATFORM = None

    def get_oauth_config(self):
        """Return OAuthConfig for this platform. Must be implemented by subclasses."""
        raise NotImplementedError

    def get_authorization_url(self, redirect_uri, state=None):
        """Build the OAuth2 authorization URL for user consent."""
        config = self.get_oauth_config()
        params = {
            'response_type': 'code',
            'client_id': config.client_id,
            'redirect_uri': redirect_uri,
            'scope': ' '.join(config.scopes),
        }
        if state:
            params['state'] = state
        return f"{config.authorize_url}?{urlencode(params)}"

    def exchange_code_for_token(self, code, redirect_uri, **kwargs):
        """Exchange an authorization code for access and refresh tokens."""
        config = self.get_oauth_config()
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': config.client_id,
            'client_secret': config.client_secret,
        }
        response = requests.post(config.token_url, data=data, timeout=30)
        response.raise_for_status()
        return response.json()

    def refresh_access_token(self, refresh_token):
        """Refresh an expired access token using the refresh token."""
        config = self.get_oauth_config()
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': config.client_id,
            'client_secret': config.client_secret,
        }
        response = requests.post(config.token_url, data=data, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_valid_token(self, device):
        """
        Ensure the device has a valid access token, refreshing if needed.
        Updates the device in-place and saves it.
        Returns the access_token string.
        """
        if device.token_expires_at and device.token_expires_at <= timezone.now():
            if not device.refresh_token:
                raise ValueError(f"Token expired for {device} and no refresh token available.")
            logger.info("Refreshing token for %s", device)
            token_data = self.refresh_access_token(device.refresh_token)
            self.update_device_tokens(device, token_data)
        return device.access_token

    def update_device_tokens(self, device, token_data):
        """Update device with new token data from OAuth response."""
        device.access_token = token_data.get('access_token', '')
        if token_data.get('refresh_token'):
            device.refresh_token = token_data['refresh_token']
        expires_in = token_data.get('expires_in')
        if expires_in:
            device.token_expires_at = timezone.now() + timedelta(seconds=int(expires_in))
        device.save(update_fields=['access_token', 'refresh_token', 'token_expires_at'])

    def api_get(self, device, endpoint, params=None):
        """Make an authenticated GET request to the platform API."""
        token = self.get_valid_token(device)
        config = self.get_oauth_config()
        url = f"{config.api_base_url}{endpoint}"
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def sync_data(self, device, start_date=None, end_date=None):
        """
        Synchronize data from the platform for the given device.
        Creates a WearableSyncLog entry and delegates to fetch_data().
        Returns the WearableSyncLog instance.
        """
        from tracker.models import WearableSyncLog
        sync_log = WearableSyncLog.objects.create(
            device=device,
            status='in_progress',
        )
        try:
            if end_date is None:
                end_date = timezone.now().date()
            if start_date is None:
                start_date = end_date - timedelta(days=7)

            records_count = self.fetch_data(device, start_date, end_date)
            sync_log.status = 'success'
            sync_log.records_synced = records_count or 0
            sync_log.completed_at = timezone.now()
            device.last_synced = timezone.now()
            device.save(update_fields=['last_synced'])
        except Exception as exc:
            logger.exception("Sync failed for %s", device)
            sync_log.status = 'failed'
            sync_log.error_message = str(exc)[:1000]
            sync_log.completed_at = timezone.now()
        sync_log.save()
        return sync_log

    def fetch_data(self, device, start_date, end_date):
        """
        Fetch data from the platform and store it in the database.
        Must be implemented by subclasses.
        Returns the number of records synced.
        """
        raise NotImplementedError
