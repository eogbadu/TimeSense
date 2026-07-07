"""Maps provider factory. Returns the configured provider (or NullMapsProvider when none is set), so
the engine's location features light up as soon as a real provider is available — without any change
to candidate generators."""

from __future__ import annotations

from app.services.recommendation.maps.provider import MapsProvider, NullMapsProvider


def get_maps_provider() -> MapsProvider:
    # A real provider (e.g. Google) is wired here in TIME-115 based on settings. Until then, the
    # NullMapsProvider keeps location candidates honest (low-confidence, no invented distances).
    return NullMapsProvider()
