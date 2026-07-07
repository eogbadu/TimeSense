"""Aggregate all domain candidate generators into one list. Async because location candidates use
the maps skill."""

from __future__ import annotations

from datetime import datetime

from app.services.recommendation.candidates.calendar_candidates import generate_calendar_candidates
from app.services.recommendation.candidates.context_switch_candidates import (
    generate_context_switch_candidates,
)
from app.services.recommendation.candidates.fallback_candidates import generate_fallback_candidates
from app.services.recommendation.candidates.health_candidates import generate_health_candidates
from app.services.recommendation.candidates.location_candidates import generate_location_candidates
from app.services.recommendation.candidates.planning_candidates import generate_planning_candidates
from app.services.recommendation.candidates.routine_candidates import generate_routine_candidates
from app.services.recommendation.candidates.task_candidates import generate_task_candidates
from app.services.recommendation.maps.maps_skill_service import MapsSkillService
from app.services.recommendation.types import CandidateAction, UserContext


async def generate_candidate_actions(
    ctx: UserContext, maps: MapsSkillService, now: datetime
) -> list[CandidateAction]:
    out: list[CandidateAction] = []
    out += generate_task_candidates(ctx, now)
    out += await generate_location_candidates(ctx, maps, now)
    out += generate_calendar_candidates(ctx, now)
    out += generate_health_candidates(ctx, now)
    out += generate_routine_candidates(ctx, now)
    out += generate_planning_candidates(ctx, now)
    out += generate_context_switch_candidates(ctx, now)
    out += generate_fallback_candidates(ctx, now)
    return out
