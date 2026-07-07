"""Context-switch candidates from current place + time + work hours."""

from __future__ import annotations

from datetime import datetime

from app.services.recommendation.types import CandidateAction, UserContext


def generate_context_switch_candidates(ctx: UserContext, now: datetime) -> list[CandidateAction]:
    out: list[CandidateAction] = []
    loc = ctx.location_context
    category = loc.location_category if loc else "unknown"
    tod = ctx.time_context.part_of_day

    if category == "home" and ctx.time_context.is_work_hours:
        out.append(CandidateAction(
            id="switch:work", type="transition_to_work", domain="context_switch",
            title="Switch into work mode", description="It's work hours — set up for focus.",
            estimated_minutes=10, urgency=0.45, importance=0.5, context_fit=0.8, time_fit=0.9,
            energy_fit=0.85, routine_fit=0.7, confidence=0.65,
            reason_codes=["ARRIVED_HOME" if False else "FOCUS_MODE_AVAILABLE"],
        ))
    if category == "work" and tod in ("evening", "night"):
        out.append(CandidateAction(
            id="switch:home", type="transition_to_home", domain="context_switch",
            title="Head home / switch off", description="The workday's winding down.",
            estimated_minutes=10, urgency=0.5, importance=0.5, context_fit=0.8, time_fit=0.9,
            energy_fit=0.8, routine_fit=0.7, confidence=0.65,
            reason_codes=["LEAVING_WORK"],
        ))
    if tod == "night":
        out.append(CandidateAction(
            id="switch:sleep", type="transition_to_sleep", domain="context_switch",
            title="Move toward sleep", description="Wind the day down and head to bed.",
            estimated_minutes=15, urgency=0.55, importance=0.6, context_fit=0.85, time_fit=0.9,
            energy_fit=1.0, routine_fit=0.75, confidence=0.72, required_energy="low",
            reason_codes=["FAMILY_TIME_WINDOW"],
        ))
    return out
