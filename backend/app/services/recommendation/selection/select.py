"""Select the winning recommendation from ranked candidates and build the typed output. Deterministic
fallback text is used here; the LLM explanation layer replaces `message`/`explanation` later."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.services.recommendation.selection.notification_policy import eligible_for_push
from app.services.recommendation.types import (
    Priority,
    Recommendation,
    ScoredCandidateAction,
    UserContext,
)

_REASON_TEXT = {
    "TASK_OVERDUE": "it's overdue",
    "TASK_DUE_TODAY": "it's due today",
    "HIGH_PRIORITY_TASK": "it's high priority",
    "QUICK_TASK_AVAILABLE": "it's quick",
    "DEEP_WORK_TASK_AVAILABLE": "you have time to focus",
    "LONG_FREE_BLOCK": "you have a long free block",
    "SHORT_FREE_BLOCK": "your free time is short",
    "NEXT_MEETING_SOON": "a meeting is coming up",
    "MEETING_STARTING_NOW": "your meeting is starting",
    "EVENT_HAS_LOCATION": "you need to travel to it",
    "POOR_SLEEP": "you slept poorly",
    "LOW_ENERGY": "your energy is low",
    "SEDENTARY_TOO_LONG": "you've been sitting a while",
    "TRIP_FITS_FREE_BLOCK": "the trip fits your free time",
    "TRIP_DOES_NOT_FIT_FREE_BLOCK": "the trip doesn't fit your free time",
    "PREFERRED_PLACE_FOUND": "it's your usual spot",
    "CLOSEST_PLACE_FOUND": "it's the closest option",
    "DRIVING_TIME_CALCULATED": "the drive time is known",
    "LOCATION_DATA_MISSING": "your location isn't available",
    "MAPS_API_UNAVAILABLE": "travel time can't be confirmed",
    "MORNING_PLANNING_WINDOW": "it's a good time to plan",
    "END_OF_DAY": "the day is wrapping up",
    "NO_CLEAR_PRIORITY": "nothing else is pressing",
    "NO_URGENT_ACTION": "nothing is urgent right now",
}


def _urgency_label(urgency: float) -> Priority:
    if urgency >= 0.8:
        return "high"
    if urgency >= 0.5:
        return "medium"
    return "low"


def _fallback_text(reason_codes: list[str]) -> str:
    parts = [_REASON_TEXT[c] for c in reason_codes if c in _REASON_TEXT]
    if not parts:
        return "This is a good fit for right now."
    uniq: list[str] = []
    for p in parts:
        if p not in uniq:
            uniq.append(p)
    parts = uniq[:3]
    if len(parts) == 1:
        body = parts[0]
    else:
        body = ", ".join(parts[:-1]) + f", and {parts[-1]}"
    return f"Best pick right now because {body}."


def select_recommendation(
    ranked: list[ScoredCandidateAction], ctx: UserContext, now: datetime
) -> Recommendation:
    best = ranked[0]
    c = best.candidate
    alternatives = [s.candidate for s in ranked[1:4]]
    explanation = _fallback_text(c.reason_codes)

    return Recommendation(
        id=str(uuid.uuid4()),
        timestamp=ctx.timestamp,
        title=c.title,
        message=explanation,
        action_type=c.type,
        domain=c.domain,
        confidence=c.confidence,
        score=best.score,
        estimated_minutes=c.estimated_minutes,
        urgency=_urgency_label(c.urgency),
        reason_codes=c.reason_codes,
        explanation=explanation,
        alternatives=alternatives,
        eligible_for_push=eligible_for_push(best.score, c.confidence),
        related_entity_ids=c.related_entity_ids,
        destination_place=c.destination_place,
        travel_estimate=c.travel_estimate,
        travel_feasibility=c.travel_feasibility,
        expires_at=c.expires_at,
    )
