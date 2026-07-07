"""Location/proximity candidates. For each task with a location intent we resolve a place and check
travel feasibility via the maps skill. If we can't confirm a real, feasible trip (no coordinates, no
maps provider, or it doesn't fit the free block) the candidate is LOW-confidence and never invents a
distance — so "Go to Walmart" can't confidently win while the user is home with no travel data."""

from __future__ import annotations

from datetime import datetime

from app.services.recommendation.candidates.common import deadline_urgency, priority_importance
from app.services.recommendation.maps.maps_skill_service import MapsSkillService
from app.services.recommendation.travel_feasibility_service import (
    TravelFeasibilityRequest,
    calculate_travel_feasibility,
)
from app.services.recommendation.types import (
    ActionType,
    CandidateAction,
    PlaceLookupRequest,
    PlaceType,
    ReasonCode,
    TaskItem,
    UserContext,
)

_TYPE_TO_ACTION: dict[PlaceType, ActionType] = {
    "grocery_store": "stop_at_grocery_store",
    "pharmacy": "stop_at_pharmacy",
    "gym": "stop_at_gym",
}


def _action_for(place_type: PlaceType | None) -> ActionType:
    if place_type in _TYPE_TO_ACTION:
        return _TYPE_TO_ACTION[place_type]
    return "run_nearby_errand"


async def _one(task: TaskItem, ctx: UserContext, maps: MapsSkillService, now: datetime) -> CandidateAction:
    intent = task.location_intent
    assert intent is not None
    on_site = float(intent.estimated_on_site_minutes or 25)
    codes: list[ReasonCode] = ["TASK_LINKED_TO_LOCATION"]

    base = CandidateAction(
        id=f"loc:{task.id}",
        type=_action_for(intent.place_type),
        domain="location",
        title=task.title,
        description=f"Errand: “{task.title}”.",
        estimated_minutes=int(on_site) + 20,
        urgency=deadline_urgency(task.due_date, now),
        importance=priority_importance(task.priority),
        context_fit=0.5,
        time_fit=0.5,
        energy_fit=0.7,
        location_fit=0.2,
        routine_fit=0.3,
        user_preference_fit=0.5,
        confidence=0.3,          # low until a feasible trip is confirmed
        required_energy="low",
        interruption_level="medium",
        requires_location=True,
        reason_codes=codes,
        related_entity_ids=[task.id],
    )

    loc = ctx.location_context
    origin = loc.coordinates if loc else None
    if origin is None:
        base.reason_codes = codes + ["LOCATION_DATA_MISSING"]
        return base
    if not maps.available:
        base.reason_codes = codes + ["MAPS_API_UNAVAILABLE"]
        return base

    place = await maps.resolve_relevant_place(PlaceLookupRequest(
        query=intent.query,
        place_type=intent.place_type,
        user_location=origin,
        preferred_places=ctx.user_preferences.preferred_places,
    ))
    if place is None:
        base.reason_codes = codes + ["MAPS_API_UNAVAILABLE"]
        return base

    codes.append("PREFERRED_PLACE_FOUND" if place.source == "user_saved" else "CLOSEST_PLACE_FOUND")
    if place.open_now is True:
        codes.append("PLACE_OPEN_NOW")
    elif place.open_now is False:
        codes.append("PLACE_CLOSED_NOW")

    feas = await calculate_travel_feasibility(
        TravelFeasibilityRequest(
            origin=origin,
            destination_place=place,
            estimated_on_site_minutes=on_site,
            mode=ctx.user_preferences.default_travel_mode,
            departure_time=ctx.timestamp,
            free_block_minutes=ctx.calendar_context.free_block_minutes,
        ),
        maps,
    )
    if feas is None:
        base.reason_codes = codes + ["MAPS_API_UNAVAILABLE"]
        return base

    codes.append("DRIVING_TIME_CALCULATED")
    base.destination_place = place
    base.travel_estimate = feas.travel_estimate
    base.travel_feasibility = feas
    base.total_required_minutes = feas.total_required_minutes
    base.fits_in_current_free_block = feas.fits_in_current_free_block
    base.distance_minutes = feas.travel_time_to_destination_minutes

    if feas.fits_in_current_free_block and place.open_now is not False:
        codes.append("TRIP_FITS_FREE_BLOCK")
        base.location_fit = 0.9
        base.time_fit = 0.85
        base.context_fit = 0.8
        base.confidence = min(0.9, feas.confidence)
    else:
        codes.append("TRIP_DOES_NOT_FIT_FREE_BLOCK")
        base.location_fit = 0.1
        base.time_fit = 0.1
        base.confidence = min(0.5, feas.confidence)

    base.reason_codes = codes
    return base


async def generate_location_candidates(
    ctx: UserContext, maps: MapsSkillService, now: datetime
) -> list[CandidateAction]:
    return [await _one(t, ctx, maps, now) for t in ctx.task_context.location_linked_tasks]
