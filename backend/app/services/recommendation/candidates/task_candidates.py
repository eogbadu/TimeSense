"""Task/productivity candidates (one per active non-location task) + a batch candidate."""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.recommendation.candidates.common import (
    deadline_urgency,
    duration_time_fit,
    energy_fit,
    priority_importance,
    task_required_energy,
)
from app.services.recommendation.types import (
    ActionType,
    CandidateAction,
    ReasonCode,
    TaskItem,
    UserContext,
)


def _classify(task: TaskItem, now: datetime) -> tuple[ActionType, list[ReasonCode]]:
    codes: list[ReasonCode] = []
    if task.due_date:
        due = datetime.fromisoformat(task.due_date)
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if due < now:
            codes.append("TASK_OVERDUE")
            return "deadline_task", codes
        if due.date() == now.date():
            codes.append("TASK_DUE_TODAY")
            return "deadline_task", codes
    if task.priority == "high":
        codes.append("HIGH_PRIORITY_TASK")
    if task.estimated_minutes is not None and task.estimated_minutes <= 15:
        codes.append("QUICK_TASK_AVAILABLE")
        return "quick_task", codes
    if task.estimated_minutes is not None and task.estimated_minutes >= 45:
        codes.append("DEEP_WORK_TASK_AVAILABLE")
        return "deep_work", codes
    if task.source == "notion":
        return "notion_task", codes
    return "admin_task", codes


def generate_task_candidates(ctx: UserContext, now: datetime) -> list[CandidateAction]:
    tc = ctx.task_context
    free = ctx.calendar_context.free_block_minutes
    user_energy = ctx.health_context.energy_estimate if ctx.health_context else None

    # Every active task gets a candidate (a low-priority task with no due date/estimate must still
    # be rankable), except location-linked tasks which the location generator handles.
    candidates: list[CandidateAction] = []
    for task in tc.all_tasks:
        if task.location_intent is not None:
            continue  # handled by the location generator
        action_type, codes = _classify(task, now)
        if task.id in ctx.recently_disagreed_task_ids:
            codes = codes + ["RECENTLY_DISAGREED"]
        req_energy = task_required_energy(task)
        candidates.append(CandidateAction(
            id=f"task:{task.id}",
            type=action_type,
            domain="task",
            title=task.title,
            description=f"Work on “{task.title}”.",
            estimated_minutes=task.estimated_minutes or 30,
            urgency=deadline_urgency(task.due_date, now),
            importance=priority_importance(task.priority),
            context_fit=0.6,
            time_fit=duration_time_fit(task.estimated_minutes, free),
            energy_fit=energy_fit(req_energy, user_energy),
            routine_fit=0.4,
            user_preference_fit=0.5,
            confidence=0.8,
            required_energy=req_energy,
            interruption_level="low",
            reason_codes=codes,
            related_entity_ids=[task.id],
        ))

    # Batch small tasks when several quick tasks exist.
    quick = [t for t in tc.quick_tasks if t.location_intent is None]
    if len(quick) >= 3:
        candidates.append(CandidateAction(
            id="task:batch",
            type="batch_small_tasks",
            domain="task",
            title="Knock out a few quick tasks",
            description=f"You have {len(quick)} short tasks — batch them together.",
            estimated_minutes=min(free or 30, 30),
            urgency=0.4,
            importance=0.5,
            context_fit=0.7,
            time_fit=0.9,
            energy_fit=0.9,
            routine_fit=0.4,
            user_preference_fit=0.5,
            confidence=0.7,
            required_energy="low",
            reason_codes=["MANY_SMALL_TASKS"],
            related_entity_ids=[t.id for t in quick],
        ))
    return candidates
