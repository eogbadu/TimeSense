"""Planning/reflection candidates: plan the day, prioritize when there's no clear priority, review
tomorrow at end of day."""

from __future__ import annotations

from datetime import datetime

from app.services.recommendation.types import CandidateAction, UserContext


def generate_planning_candidates(ctx: UserContext, now: datetime) -> list[CandidateAction]:
    out: list[CandidateAction] = []
    tod = ctx.time_context.part_of_day
    tc = ctx.task_context
    has_tasks = bool(tc.overdue_tasks or tc.due_today_tasks or tc.high_priority_tasks
                     or tc.quick_tasks or tc.deep_work_tasks)

    if tod in ("early_morning", "morning"):
        out.append(CandidateAction(
            id="plan:day", type="plan_day", domain="planning",
            title="Plan your day", description="Set today's priorities before the day fills up.",
            estimated_minutes=10, urgency=0.45, importance=0.55, context_fit=0.75, time_fit=0.95,
            energy_fit=0.9, routine_fit=0.6, confidence=0.72,
            reason_codes=["MORNING_PLANNING_WINDOW"],
        ))
    if tod in ("evening", "night"):
        out.append(CandidateAction(
            id="plan:tomorrow", type="review_tomorrow", domain="planning",
            title="Review tomorrow", description="Glance at what's coming so tomorrow starts smooth.",
            estimated_minutes=10, urgency=0.4, importance=0.5, context_fit=0.75, time_fit=0.95,
            energy_fit=0.85, routine_fit=0.6, confidence=0.7,
            reason_codes=["END_OF_DAY"],
        ))
    if not has_tasks:
        out.append(CandidateAction(
            id="plan:prioritize", type="prioritize_tasks", domain="planning",
            title="Line up what matters", description="No clear priority right now — capture and rank a few things.",
            estimated_minutes=10, urgency=0.35, importance=0.5, context_fit=0.7, time_fit=0.95,
            energy_fit=0.85, confidence=0.6,
            reason_codes=["NO_CLEAR_PRIORITY"],
        ))
    return out
