"""Google Maps implementation of ``MapsProvider`` (geocoding, nearby places, travel time via the
Distance Matrix API). Async httpx; every method swallows errors and returns None/[] so a maps outage
never breaks the recommendation engine (the candidate just degrades to low-confidence)."""

from __future__ import annotations

import httpx

from app.services.recommendation.types import (
    Coordinates,
    Place,
    PlaceLookupRequest,
    PlaceType,
    TravelEstimate,
    TravelEstimateRequest,
    TravelMode,
)

_GEOCODE = "https://maps.googleapis.com/maps/api/geocode/json"
_NEARBY = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
_TEXT = "https://maps.googleapis.com/maps/api/place/textsearch/json"
_DISTANCE = "https://maps.googleapis.com/maps/api/distancematrix/json"

_MODE: dict[TravelMode, str] = {
    "driving": "driving", "walking": "walking", "transit": "transit", "bicycling": "bicycling",
}


class GoogleMapsProvider:
    def __init__(self, api_key: str, timeout: float = 6.0) -> None:
        self._key = api_key
        self._timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self._key)

    async def _get(self, url: str, params: dict) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, params={**params, "key": self._key})
            if resp.status_code != 200:
                return None
            return resp.json()
        except Exception:
            return None

    async def geocode(self, address: str) -> Coordinates | None:
        data = await self._get(_GEOCODE, {"address": address})
        if not data or data.get("status") != "OK" or not data.get("results"):
            return None
        loc = data["results"][0]["geometry"]["location"]
        return Coordinates(latitude=loc["lat"], longitude=loc["lng"])

    async def search_nearby(self, request: PlaceLookupRequest) -> list[Place]:
        if request.user_location is not None:
            params = {
                "keyword": request.query,
                "location": f"{request.user_location.latitude},{request.user_location.longitude}",
                "rankby": "distance",
            }
            data = await self._get(_NEARBY, params)
        else:
            data = await self._get(_TEXT, {"query": request.query})
        if not data or data.get("status") not in ("OK", "ZERO_RESULTS"):
            return None if data is None else []
        out: list[Place] = []
        for r in (data.get("results") or [])[: max(1, request.max_results)]:
            loc = r.get("geometry", {}).get("location")
            if not loc:
                continue
            open_now = None
            if isinstance(r.get("opening_hours"), dict) and "open_now" in r["opening_hours"]:
                open_now = bool(r["opening_hours"]["open_now"])
            out.append(Place(
                id=r.get("place_id", r.get("name", "")),
                name=r.get("name", request.query),
                type=request.place_type or _guess_type(r.get("types", [])),
                coordinates=Coordinates(latitude=loc["lat"], longitude=loc["lng"]),
                address=r.get("vicinity") or r.get("formatted_address"),
                source="maps_api",
                open_now=open_now,
                confidence=0.85,
            ))
        return out

    async def travel_estimate(self, request: TravelEstimateRequest) -> TravelEstimate | None:
        params = {
            "origins": f"{request.origin.latitude},{request.origin.longitude}",
            "destinations": f"{request.destination.latitude},{request.destination.longitude}",
            "mode": _MODE.get(request.mode, "driving"),
        }
        if request.departure_time:
            params["departure_time"] = "now"
        data = await self._get(_DISTANCE, params)
        if not data or data.get("status") != "OK":
            return None
        try:
            element = data["rows"][0]["elements"][0]
        except (KeyError, IndexError):
            return None
        if element.get("status") != "OK":
            return None
        meters = element["distance"]["value"]
        seconds = element.get("duration_in_traffic", element["duration"])["value"]
        return TravelEstimate(
            distance_meters=float(meters),
            distance_miles=round(meters / 1609.344, 1),
            duration_seconds=float(seconds),
            duration_minutes=round(seconds / 60.0, 1),
            mode=request.mode,
            source="maps_api",
            confidence=0.9,
        )


def _guess_type(types: list[str]) -> PlaceType:
    mapping: dict[str, PlaceType] = {
        "supermarket": "grocery_store", "grocery_or_supermarket": "grocery_store",
        "pharmacy": "pharmacy", "drugstore": "pharmacy", "gym": "gym", "school": "school",
        "restaurant": "restaurant", "gas_station": "gas_station",
    }
    for t in types:
        if t in mapping:
            return mapping[t]
    return "store"
