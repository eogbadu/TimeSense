"""Shared 0..1 sub-score helpers used by the candidate generators. Deterministic and pure."""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.recommendation.types import Energy, Priority, TaskItem


def deadline_urgency(due_iso: str | None, now: datetime) -> float:
    if not due_iso:
        return 0.35
    due = datetime.fromisoformat(due_iso)
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    seconds = (due - now).total_seconds()
    if seconds <= 0:
        return 1.0                       # overdue
    if seconds < 24 * 3600:
        return 0.8                       # due today
    if seconds < 3 * 24 * 3600:
        return 0.5                       # due soon
    return 0.25                          # future


def priority_importance(priority: Priority) -> float:
    return {"high": 0.9, "medium": 0.6, "low": 0.3}[priority]


def duration_time_fit(estimated_minutes: int | None, free_block_minutes: int | None) -> float:
    if free_block_minutes is None:
        return 0.7
    if estimated_minutes is None:
        return 0.6
    if estimated_minutes <= free_block_minutes:
        return 1.0
    # exceeds the window — the more it overshoots, the worse
    overshoot = estimated_minutes - free_block_minutes
    return 0.3 if overshoot <= 15 else 0.1


def energy_fit(required: Energy, user_energy: Energy | None) -> float:
    if user_energy is None:
        return 0.6
    rank = {"low": 0, "medium": 1, "high": 2}
    # high-energy tasks fit poorly when the user is low; low-energy tasks always fit
    if rank[required] <= rank[user_energy]:
        return 1.0
    gap = rank[required] - rank[user_energy]
    return 0.5 if gap == 1 else 0.2


def task_required_energy(task: TaskItem) -> Energy:
    if task.estimated_minutes is not None and task.estimated_minutes >= 45:
        return "high"
    if task.estimated_minutes is not None and task.estimated_minutes <= 15:
        return "low"
    return "medium"
