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


# How demanding a task is, translated into the energy it needs. Difficulty is a property of the
# WORK; duration is not. A 90-minute flight is light, a 10-minute difficult call is not.
_DIFFICULTY_TO_ENERGY: dict[str, Energy] = {
    "light": "low",
    "moderate": "medium",
    "deep": "high",
}


def task_required_energy(task: TaskItem, adaptation: dict | None = None) -> Energy:
    """How much capacity this task needs.

    Was derived purely from estimated duration (>= 45 min counted as high energy, <= 15 as low), so
    a 90-minute podcast looked demanding and a 10-minute code review trivial. Difficulty from the
    baseline library (TIME-284) is the real signal; duration is now only a fallback for tasks that
    predate classification (TIME-290).

    The per-user adjustment: someone who reliably finishes demanding work while their energy is low
    doesn't need to be protected from it. That evidence comes from the TIME-292 profile, and only
    applies once there is enough of it — otherwise everyone gets the library's own mapping.
    """
    base = _DIFFICULTY_TO_ENERGY.get((task.difficulty or "").strip().lower())
    if base is None:
        # No classification (a row created before TIME-285): fall back to the old heuristic rather
        # than guessing "medium" for everything.
        if task.estimated_minutes is not None and task.estimated_minutes >= 45:
            base = "high"
        elif task.estimated_minutes is not None and task.estimated_minutes <= 15:
            base = "low"
        else:
            base = "medium"

    return _adjust_for_user(base, adaptation)


# Below this many observed completions we don't claim to know anything about the user's tolerance.
_TOLERANCE_MIN_SAMPLES = 8
# The share of completed work that has to happen at low energy before we stop treating demanding
# work as something to protect them from.
_TOLERANCE_SHARE = 0.4


def _adjust_for_user(required: Energy, adaptation: dict | None) -> Energy:
    """Soften the requirement for a user who demonstrably works fine when depleted.

    This is deliberately one-directional. Relaxing a requirement lets the engine offer something it
    would otherwise have suppressed, which the user can decline. RAISING one would silently hide
    work from someone whose data merely looks unusual, which is a much worse failure — so it isn't
    done.
    """
    if required != "high" or not adaptation:
        return required
    counts = adaptation.get("completions_by_energy") or {}
    total = sum(counts.values()) if counts else 0
    if total < _TOLERANCE_MIN_SAMPLES:
        return required
    low_share = counts.get("low", 0) / total
    return "medium" if low_share >= _TOLERANCE_SHARE else required
