"""Routine/habit candidates keyed off time-of-day + work-hours windows."""

from __future__ import annotations

from datetime import datetime

from app.services.recommendation.types import CandidateAction, UserContext


def generate_routine_candidates(ctx: UserContext, now: datetime) -> list[CandidateAction]:
    out: list[CandidateAction] = []
    tod = ctx.time_context.part_of_day
    hour = ctx.time_context.hour

    if tod == "early_morning":
        out.append(CandidateAction(
            id="routine:morning", type="morning_routine", domain="routine",
            title="Morning routine", description="Ease into the day with your usual start.",
            estimated_minutes=20, urgency=0.45, importance=0.5, context_fit=0.75, time_fit=0.9,
            energy_fit=0.9, routine_fit=0.9, confidence=0.7, required_energy="low",
            reason_codes=["MORNING_ROUTINE_WINDOW"],
        ))
    if tod in ("evening", "night"):
        out.append(CandidateAction(
            id="routine:evening", type="evening_routine", domain="routine",
            title="Evening routine", description="Wrap up the day.",
            estimated_minutes=20, urgency=0.4, importance=0.45, context_fit=0.75, time_fit=0.9,
            energy_fit=0.9, routine_fit=0.85, confidence=0.7, required_energy="low",
            reason_codes=["EVENING_ROUTINE_WINDOW"],
        ))

    wh = ctx.user_preferences.work_hours
    if wh is not None:
        try:
            start_h = int(wh.start.split(":")[0])
            end_h = int(wh.end.split(":")[0])
        except (ValueError, IndexError):
            start_h, end_h = -1, -1
        if start_h >= 0 and hour == start_h and not ctx.time_context.is_weekend:
            out.append(CandidateAction(
                id="routine:workstart", type="work_start_routine", domain="routine",
                title="Start your workday", description="Kick off with your work-start routine.",
                estimated_minutes=10, urgency=0.5, importance=0.55, context_fit=0.8, time_fit=0.9,
                energy_fit=0.85, routine_fit=0.85, confidence=0.72,
                reason_codes=["WORK_START_WINDOW"],
            ))
        if end_h >= 0 and hour == max(end_h - 1, 0) and not ctx.time_context.is_weekend:
            out.append(CandidateAction(
                id="routine:shutdown", type="work_shutdown_routine", domain="routine",
                title="Wind down work", description="Close out the workday cleanly.",
                estimated_minutes=15, urgency=0.5, importance=0.55, context_fit=0.8, time_fit=0.9,
                energy_fit=0.8, routine_fit=0.85, confidence=0.72,
                reason_codes=["WORK_SHUTDOWN_WINDOW"],
            ))
    return out
