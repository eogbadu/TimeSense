"""Build a typed ``UserContext`` from the database for the live engine. Maps ORM ``Task`` rows to the
engine's ``TaskItem`` (including light location-intent detection), pulls the current place, latest
sleep-derived health, and preferences. Free-block minutes come from the caller (UsableTimeService)."""

from __future__ import annotations

import dataclasses
from datetime import datetime, time, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.repositories.sleep_wake_repository import SleepWakeRepository
from app.services.recommendation.location_service import get_user_location_snapshot
from app.services.recommendation.normalize_context import RawContextInputs, normalize_context
from app.services.recommendation.time_service import get_time_snapshot
from app.services.recommendation.types import (
    HealthContext,
    LocationIntent,
    PlaceType,
    Priority,
    TaskItem,
    TaskStatus,
    UserContext,
    WorkHours,
)
from app.services.recommendation.types import UserPreferences as EngPreferences

# --- light location-intent detection (conservative to avoid false positives) ---

_PLACE_KEYWORDS: dict[str, PlaceType] = {
    "walmart": "walmart", "target": "target", "costco": "costco",
    "grocery": "grocery_store", "groceries": "grocery_store", "supermarket": "grocery_store",
    "pharmacy": "pharmacy", "cvs": "pharmacy", "walgreens": "pharmacy", "medicine": "pharmacy",
    "gym": "gym", "school": "school", "gas": "gas_station",
}
_TRIGGER_PHRASES = ("go to", "stop by", "stop at", "pick up", "drop off", "run to", "head to")


def detect_location_intent(title: str) -> LocationIntent | None:
    t = title.lower()
    for kw, ptype in _PLACE_KEYWORDS.items():
        if kw in t:
            return LocationIntent(query=title, place_type=ptype, requires_travel=True)
    if any(p in t for p in _TRIGGER_PHRASES):
        return LocationIntent(query=title, place_type=None, requires_travel=True)
    return None


def _priority(p: int) -> Priority:
    if p <= 2:
        return "high"
    if p == 3:
        return "medium"
    return "low"


def _status(s: str) -> TaskStatus:
    if s == "in_progress":
        return "in_progress"
    if s == "done":
        return "completed"
    return "not_started"


def _to_task_item(task: Task) -> TaskItem:
    due = None
    if task.due_at is not None:
        due = (task.due_at if task.due_at.tzinfo else task.due_at.replace(tzinfo=timezone.utc)).isoformat()
    src = getattr(task, "source", None)
    source = src if src in ("notion", "reminder", "calendar", "manual") else "manual"
    return TaskItem(
        id=str(task.id),
        title=task.title,
        source=source,
        priority=_priority(task.priority),
        status=_status(task.status),
        estimated_minutes=task.estimated_minutes,
        due_date=due,
        location_intent=detect_location_intent(task.title),
    )


async def _health(db: AsyncSession, user_id, now: datetime) -> HealthContext | None:
    ev = await SleepWakeRepository(db).get_latest_today(user_id)
    if ev is None:
        return None
    sleep_hours = None
    if ev.sleep_start is not None:
        start = ev.sleep_start if ev.sleep_start.tzinfo else ev.sleep_start.replace(tzinfo=timezone.utc)
        wake = ev.wake_time if ev.wake_time.tzinfo else ev.wake_time.replace(tzinfo=timezone.utc)
        sleep_hours = round((wake - start).total_seconds() / 3600, 1)
    if sleep_hours is None:
        energy, quality = "medium", None
    elif sleep_hours >= 7.5:
        energy, quality = "high", "good"
    elif sleep_hours >= 6:
        energy, quality = "medium", "okay"
    else:
        energy, quality = "low", "poor"
    return HealthContext(sleep_hours=sleep_hours, sleep_quality=quality, energy_estimate=energy)


async def build_user_context(
    db: AsyncSession, user, candidate_tasks: list[Task], now: datetime, usable_minutes: int
) -> tuple[UserContext, dict[str, Task]]:
    tz = user.profile.timezone if user.profile else "UTC"
    prefs = user.preferences
    work_start = prefs.work_start_hour if prefs else 9
    work_end = prefs.work_end_hour if prefs else 17

    task_items = [_to_task_item(t) for t in candidate_tasks]
    task_map = {str(t.id): t for t in candidate_tasks}

    snapshot = get_time_snapshot(
        tz, now=now, work_start=time(work_start, 0), work_end=time(work_end, 0)
    )
    location = await get_user_location_snapshot(db, user.id, now)
    health = await _health(db, user.id, now)

    raw = RawContextInputs(
        now=now, timezone=tz, time_snapshot=snapshot,
        preferences=EngPreferences(
            work_hours=WorkHours(f"{work_start:02d}:00", f"{work_end:02d}:00"),
            default_travel_mode="driving",
        ),
        tasks=task_items, calendar_events=[], location_snapshot=location, health=health,
    )
    ctx = normalize_context(raw)
    # No calendar integration yet → use the real usable window as the free block.
    ctx = dataclasses.replace(
        ctx,
        calendar_context=dataclasses.replace(
            ctx.calendar_context, free_block_minutes=usable_minutes, minutes_until_next_event=None
        ),
    )
    return ctx, task_map
