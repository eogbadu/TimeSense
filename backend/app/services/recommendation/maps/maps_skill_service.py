"""MapsSkillService — the single wrapper every candidate generator uses for maps functionality.
Candidate generators must NOT call a maps provider directly. This service adds the resolution policy
(preferred places first, then nearby search ranked by relevance/distance/open/confidence) on top of
whatever provider is injected."""

from __future__ import annotations

import math

from app.services.recommendation.maps.provider import MapsProvider, NullMapsProvider
from app.services.recommendation.types import (
    Coordinates,
    Place,
    PlaceLookupRequest,
    TravelEstimate,
    TravelEstimateRequest,
)


def haversine_meters(a: Coordinates, b: Coordinates) -> float:
    """Great-circle distance in meters (used only to rank already-resolved places by proximity —
    never to fabricate a driving time)."""
    r = 6_371_000.0
    p1, p2 = math.radians(a.latitude), math.radians(b.latitude)
    dphi = math.radians(b.latitude - a.latitude)
    dlmb = math.radians(b.longitude - a.longitude)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def _matches(place: Place, request: PlaceLookupRequest) -> bool:
    if request.place_type is not None and place.type == request.place_type:
        return True
    q = request.query.strip().lower()
    return bool(q) and (q in place.name.lower() or (place.address or "").lower().find(q) >= 0)


class MapsSkillService:
    def __init__(self, provider: MapsProvider | None = None) -> None:
        self.provider: MapsProvider = provider or NullMapsProvider()

    @property
    def available(self) -> bool:
        return self.provider.available

    async def geocode_address(self, address: str) -> Coordinates | None:
        return await self.provider.geocode(address)

    async def search_nearby_places(self, request: PlaceLookupRequest) -> list[Place]:
        return await self.provider.search_nearby(request)

    async def get_travel_estimate(self, request: TravelEstimateRequest) -> TravelEstimate | None:
        return await self.provider.travel_estimate(request)

    async def resolve_relevant_place(self, request: PlaceLookupRequest) -> Place | None:
        """1) preferred places first; 2) else nearby search; 3) rank by relevance/distance/open/
        confidence; 4) return the best. Returns None when nothing matches or maps is unavailable."""
        preferred = [p for p in request.preferred_places if _matches(p, request)]
        if preferred:
            return self._best(preferred, request.user_location)
        if request.preferred_only or not self.provider.available:
            return None
        nearby = await self.provider.search_nearby(request)
        candidates = [p for p in nearby if _matches(p, request)] or nearby
        return self._best(candidates, request.user_location) if candidates else None

    def _best(self, places: list[Place], origin: Coordinates | None) -> Place | None:
        if not places:
            return None

        def rank(p: Place) -> tuple[int, float, float]:
            # open places first (unknown counts as open), then nearest, then highest confidence
            open_rank = 0 if p.open_now is not False else 1
            dist = (
                haversine_meters(origin, p.coordinates)
                if origin is not None else 0.0
            )
            return (open_rank, dist, -p.confidence)

        return sorted(places, key=rank)[0]
