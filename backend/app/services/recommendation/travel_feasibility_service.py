"""Travel feasibility — does a location-based action actually fit the user's available time?

totalRequired = travelTo + onSite + travelAfter + buffer   (buffer defaults to 10 min)

If the maps skill can't produce a travel estimate, this returns None — the engine then skips or
low-confidences the candidate rather than guessing. If totalRequired exceeds the free block, the
result is marked not-fitting (the scorer applies a heavy penalty / rejects it)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.services.recommendation.maps.maps_skill_service import MapsSkillService
from app.services.recommendation.types import (
    Coordinates,
    Place,
    TravelEstimateRequest,
    TravelFeasibility,
    TravelMode,
)

DEFAULT_BUFFER_MINUTES = 10.0


@dataclass(frozen=True)
class TravelFeasibilityRequest:
    origin: Coordinates
    destination_place: Place
    estimated_on_site_minutes: float
    mode: TravelMode
    departure_time: str
    free_block_minutes: Optional[float] = None
    next_relevant_location: Optional[Coordinates] = None
    buffer_minutes: float = DEFAULT_BUFFER_MINUTES


async def calculate_travel_feasibility(
    request: TravelFeasibilityRequest, maps: MapsSkillService
) -> TravelFeasibility | None:
    to_estimate = await maps.get_travel_estimate(
        TravelEstimateRequest(
            origin=request.origin,
            destination=request.destination_place.coordinates,
            mode=request.mode,
            departure_time=request.departure_time,
        )
    )
    if to_estimate is None:
        return None   # no reliable travel time — do not guess

    travel_to = to_estimate.duration_minutes

    travel_after: Optional[float] = None
    if request.next_relevant_location is not None:
        after = await maps.get_travel_estimate(
            TravelEstimateRequest(
                origin=request.destination_place.coordinates,
                destination=request.next_relevant_location,
                mode=request.mode,
            )
        )
        travel_after = after.duration_minutes if after is not None else None

    total = travel_to + request.estimated_on_site_minutes + (travel_after or 0.0) + request.buffer_minutes

    if request.free_block_minutes is None:
        fits = True                      # unknown window — can't reject, but lower the confidence
        confidence = min(to_estimate.confidence, 0.5)
    else:
        fits = total <= request.free_block_minutes
        confidence = to_estimate.confidence

    return TravelFeasibility(
        destination_place=request.destination_place,
        travel_estimate=to_estimate,
        travel_time_to_destination_minutes=travel_to,
        estimated_on_site_minutes=request.estimated_on_site_minutes,
        travel_time_after_task_minutes=travel_after,
        buffer_minutes=request.buffer_minutes,
        total_required_minutes=total,
        free_block_minutes=request.free_block_minutes,
        fits_in_current_free_block=fits,
        confidence=confidence,
    )
