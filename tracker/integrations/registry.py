"""
Registry for wearable platform integration clients.

Provides a lookup function to get the appropriate OAuth client
for a given platform identifier.
"""
from .withings import WithingsClient
from .google_fit import GoogleFitClient
from .fitbit import FitbitClient
from .oura import OuraClient
from .strava import StravaClient
from .garmin import GarminClient
from .dexcom import DexcomClient
from .samsung_health import SamsungHealthClient

# Map platform identifiers (matching WEARABLE_PLATFORMS in models.py)
# to their client classes.
PLATFORM_CLIENTS = {
    'withings': WithingsClient,
    'google_fit': GoogleFitClient,
    'fitbit': FitbitClient,
    'oura': OuraClient,
    'strava': StravaClient,
    'garmin': GarminClient,
    'dexcom_cgm': DexcomClient,
    'samsung_health': SamsungHealthClient,
}

# Platforms that support OAuth2-based connection
OAUTH_PLATFORMS = {
    'withings', 'google_fit', 'fitbit', 'oura', 'strava',
    'garmin', 'dexcom_cgm', 'samsung_health',
}

# apple_health does not have a web-based OAuth API; data is typically
# imported via file upload (XML export) or a mobile companion app.
NON_OAUTH_PLATFORMS = {'apple_health'}


def get_client(platform):
    """
    Get an integration client instance for the given platform.
    Returns None if the platform is not supported for OAuth.
    """
    client_class = PLATFORM_CLIENTS.get(platform)
    if client_class:
        return client_class()
    return None


def is_oauth_platform(platform):
    """Return True if the platform supports OAuth-based connection."""
    return platform in OAUTH_PLATFORMS
