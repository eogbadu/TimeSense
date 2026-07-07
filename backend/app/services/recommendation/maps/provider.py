"""Maps provider abstraction. The engine stays independent of the underlying maps API (Google,
Apple, Mapbox, …) — providers implement this Protocol. ``NullMapsProvider`` is the default while no
API key/coordinates are configured: it returns None everywhere, so location candidates degrade to
low-confidence (per the spec's failure rules) rather than inventing distances."""

from __future__ import annotations

from typing import Protocol

from app.services.recommendation.types import (
    Coordinates,
    Place,
    PlaceLookupRequest,
    TravelEstimate,
    TravelEstimateRequest,
)


class MapsProvider(Protocol):
    """A maps backend. All methods are async and must never raise — return None/[] on failure so the
    engine can degrade gracefully."""

    @property
    def available(self) -> bool:
        ...

    async def geocode(self, address: str) -> Coordinates | None:
        ...

    async def search_nearby(self, request: PlaceLookupRequest) -> list[Place]:
        ...

    async def travel_estimate(self, request: TravelEstimateRequest) -> TravelEstimate | None:
        ...


class NullMapsProvider:
    """No maps backend configured. Everything resolves to None/empty — the engine then marks
    location-based candidates low-confidence and never fabricates travel times."""

    @property
    def available(self) -> bool:
        return False

    async def geocode(self, address: str) -> Coordinates | None:
        return None

    async def search_nearby(self, request: PlaceLookupRequest) -> list[Place]:
        return []

    async def travel_estimate(self, request: TravelEstimateRequest) -> TravelEstimate | None:
        return None
