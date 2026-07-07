"""Maps provider factory. Returns the configured provider (or NullMapsProvider when none is set), so
the engine's location features light up as soon as a real provider is available — without any change
to candidate generators."""

from __future__ import annotations

from app.core.config import settings
from app.services.recommendation.maps.google_provider import GoogleMapsProvider
from app.services.recommendation.maps.provider import MapsProvider, NullMapsProvider


def get_maps_provider() -> MapsProvider:
    """Return the configured maps provider. With a Google Maps API key, location features go live;
    without one, the NullMapsProvider keeps candidates honest (low-confidence, no invented distances)."""
    key = settings.google_maps_api_key
    if key:
        return GoogleMapsProvider(key)
    return NullMapsProvider()
