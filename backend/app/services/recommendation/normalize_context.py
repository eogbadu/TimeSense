"""Normalize raw, already-fetched inputs into a typed ``UserContext``. Pure/deterministic — no DB
access, no ``datetime.now()`` (the caller injects ``now`` and the time snapshot), so it's fully
testable. DB fetching + assembly lives in the integration layer (later phase)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.services.recommendation.time_service import minutes_between
from app.services.recommendation.types import (
    CalendarContext,
    CalendarEvent,
    HealthContext,
    Level,
    TaskContext,
    TaskItem,
    TimeSnapshot,
    UserContext,
    UserLocationSnapshot,
    UserPreferences,
)

QUICK_TASK_MAX_MINUTES = 15
DEEP_WORK_MIN_MINUTES = 45
# When there's no next event, treat the free block as this many minutes (a generous open window).
OPEN_FREE_BLOCK_MINUTES = 180


@dataclass
class RawContextInputs:
    now: datetime
    timezone: str
    time_snapshot: TimeSnapshot
    preferences: UserPreferences
    tasks: list[TaskItem] = field(default_factory=list)
    calendar_events: list[CalendarEvent] = field(default_factory=list)
    location_snapshot: Optional[UserLocationSnapshot] = None
    health: Optional[HealthContext] = None


def _parse(iso: str) -> datetime:
    dt = datetime.fromisoformat(iso)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _meeting_density(count: int) -> Level:
    if count >= 5:
        return "high"
    if count >= 2:
        return "medium"
    return "low"


def _calendar_context(events: list[CalendarEvent], now: datetime) -> CalendarContext:
    current: Optional[CalendarEvent] = None
    upcoming: list[tuple[datetime, CalendarEvent]] = []
    today_count = 0
    for ev in events:
        start, end = _parse(ev.start_time), _parse(ev.end_time)
        if start.date() == now.date():
            today_count += 1
        if start <= now < end:
            current = ev
        elif start > now:
            upcoming.append((start, ev))

    upcoming.sort(key=lambda pair: pair[0])
    next_event = upcoming[0][1] if upcoming else None
    minutes_until = minutes_between(now, upcoming[0][0]) if upcoming else None
    free_block = minutes_until if minutes_until is not None else OPEN_FREE_BLOCK_MINUTES

    return CalendarContext(
        has_hard_deadline_today=False,  # filled in by _task derived flags below via normalize
        meeting_density_today=_meeting_density(today_count),
        current_event=current,
        next_event=next_event,
        minutes_until_next_event=minutes_until,
        free_block_minutes=free_block,
    )


def _task_context(tasks: list[TaskItem], now: datetime) -> tuple[TaskContext, bool]:
    active = [t for t in tasks if t.status in ("not_started", "in_progress")]
    overdue: list[TaskItem] = []
    due_today: list[TaskItem] = []
    high: list[TaskItem] = []
    quick: list[TaskItem] = []
    deep: list[TaskItem] = []
    location_linked: list[TaskItem] = []

    for t in active:
        if t.due_date:
            due = _parse(t.due_date)
            if due < now:
                overdue.append(t)
            elif due.date() == now.date():
                due_today.append(t)
        if t.priority == "high":
            high.append(t)
        if t.estimated_minutes is not None and t.estimated_minutes <= QUICK_TASK_MAX_MINUTES:
            quick.append(t)
        if t.estimated_minutes is not None and t.estimated_minutes >= DEEP_WORK_MIN_MINUTES:
            deep.append(t)
        if t.location_intent is not None:
            location_linked.append(t)

    has_hard_deadline_today = bool(overdue or due_today)
    ctx = TaskContext(
        overdue_tasks=overdue,
        due_today_tasks=due_today,
        high_priority_tasks=high,
        quick_tasks=quick,
        deep_work_tasks=deep,
        location_linked_tasks=location_linked,
    )
    return ctx, has_hard_deadline_today


def normalize_context(raw: RawContextInputs) -> UserContext:
    now = raw.now if raw.now.tzinfo else raw.now.replace(tzinfo=timezone.utc)

    calendar = _calendar_context(raw.calendar_events, now)
    task_ctx, has_deadline = _task_context(raw.tasks, now)

    calendar = CalendarContext(
        has_hard_deadline_today=has_deadline,
        meeting_density_today=calendar.meeting_density_today,
        current_event=calendar.current_event,
        next_event=calendar.next_event,
        minutes_until_next_event=calendar.minutes_until_next_event,
        free_block_minutes=calendar.free_block_minutes,
    )

    return UserContext(
        timestamp=now.astimezone(timezone.utc).isoformat(),
        timezone=raw.timezone,
        time_context=raw.time_snapshot,
        calendar_context=calendar,
        task_context=task_ctx,
        user_preferences=raw.preferences,
        location_context=raw.location_snapshot,
        health_context=raw.health,
    )
