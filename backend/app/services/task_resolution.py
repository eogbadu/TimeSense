"""
Passed deadlines that need a decision, not a louder reminder (TIME-309).

`deadline_urgency` returns 1.0 for anything overdue, forever, with no decay. A task whose deadline
has passed therefore leads the recommendation on maximum urgency indefinitely — a user was shown one
that had been due a WEEK earlier, at midnight, as the single best thing to do next.

A passed deadline is not information about what to do now. It is a signal that something needs
resolving: the date was wrong, the task is done, or it no longer matters. The app's job is to ask,
not to keep shouting the same answer.

The rule deliberately keys on the DAY, not the instant. A task due at 8pm is not stale at 8:05pm —
the user is plausibly still on it, and nagging there would be exactly the "another job to manage"
failure the product brief forbids. It becomes stale once it has survived into the next day.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.localtime import local_today, resolve_zone


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def is_awaiting_resolution(due_at: datetime | None, now: datetime, tz_name: str | None) -> bool:
    """True when a task's deadline fell on an earlier local day than today.

    Not "due_at < now" — that would make a task stale five minutes after its own deadline, while the
    user is most likely still working on it.
    """
    if due_at is None:
        return False
    due_local_date = _aware(due_at).astimezone(resolve_zone(tz_name)).date()
    return due_local_date < local_today(tz_name, now)


def days_overdue(due_at: datetime | None, now: datetime, tz_name: str | None) -> int:
    """Whole local days between the deadline's day and today. 0 when not yet stale.

    Counted in local calendar days rather than elapsed hours so it matches how the deadline reads to
    the user: something due yesterday evening is "1 day", not "0" because 20 hours have passed.
    """
    if due_at is None:
        return 0
    due_local_date = _aware(due_at).astimezone(resolve_zone(tz_name)).date()
    delta = (local_today(tz_name, now) - due_local_date).days
    return max(0, delta)


def awaiting_resolution_ids(tasks, now: datetime, tz_name: str | None) -> set[str]:
    """Ids (as strings, matching the engine's candidate ids) of tasks whose deadline has passed."""
    return {
        str(t.id)
        for t in tasks
        if is_awaiting_resolution(getattr(t, "due_at", None), now, tz_name)
    }
