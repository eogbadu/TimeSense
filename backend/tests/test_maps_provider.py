"""TIME-115 — maps provider factory + Google provider gating/parsing (no real network calls)."""

import pytest

from app.services.recommendation.maps.google_provider import GoogleMapsProvider
from app.services.recommendation.maps.provider import NullMapsProvider
from app.services.recommendation.types import Coordinates, TravelEstimateRequest

pytestmark = pytest.mark.anyio


async def test_factory_returns_null_without_key(monkeypatch):
    from app.services.recommendation.maps import factory
    monkeypatch.setattr(factory.settings, "google_maps_api_key", "", raising=False)
    assert isinstance(factory.get_maps_provider(), NullMapsProvider)


async def test_factory_returns_google_with_key(monkeypatch):
    from app.services.recommendation.maps import factory
    monkeypatch.setattr(factory.settings, "google_maps_api_key", "test-key", raising=False)
    provider = factory.get_maps_provider()
    assert isinstance(provider, GoogleMapsProvider) and provider.available is True


async def test_google_provider_unavailable_without_key():
    assert GoogleMapsProvider("").available is False


async def test_google_travel_estimate_parses_distance_matrix(monkeypatch):
    provider = GoogleMapsProvider("k")

    async def fake_get(url, params):
        return {
            "status": "OK",
            "rows": [{"elements": [{
                "status": "OK",
                "distance": {"value": 9660},
                "duration": {"value": 720},
            }]}],
        }

    monkeypatch.setattr(provider, "_get", fake_get)
    est = await provider.travel_estimate(
        TravelEstimateRequest(Coordinates(40.0, -75.0), Coordinates(40.1, -75.1), "driving")
    )
    assert est is not None
    assert est.duration_minutes == 12.0 and est.distance_miles == 6.0 and est.source == "maps_api"


async def test_google_travel_estimate_none_on_error(monkeypatch):
    provider = GoogleMapsProvider("k")

    async def fake_get(url, params):
        return {"status": "REQUEST_DENIED"}

    monkeypatch.setattr(provider, "_get", fake_get)
    est = await provider.travel_estimate(
        TravelEstimateRequest(Coordinates(0, 0), Coordinates(1, 1), "driving")
    )
    assert est is None  # never invents a time
