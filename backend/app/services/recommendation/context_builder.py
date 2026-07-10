"""Build a typed ``UserContext`` from the database for the live engine. Maps ORM ``Task`` rows to the
engine's ``TaskItem`` (including light location-intent detection), pulls the current place, latest
sleep-derived health, and preferences. Free-block minutes come from the caller (UsableTimeService)."""

from __future__ import annotations

import dataclasses
from datetime import datetime, time, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.user_place import UserPlace
from app.repositories.recommendation_feedback_repository import RecommendationFeedbackRepository
from app.repositories.sleep_wake_repository import SleepWakeRepository
from app.repositories.synced_calendar_event_repository import SyncedCalendarEventRepository
from app.repositories.user_place_repository import UserPlaceRepository
from app.services.recommendation.location_service import get_user_location_snapshot
from app.services.recommendation.normalize_context import RawContextInputs, normalize_context
from app.services.recommendation.time_service import get_time_snapshot
from app.services.recommendation.types import (
    CalendarEvent,
    Coordinates,
    HealthContext,
    LocationIntent,
    Place,
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


def _location_intent(task: Task) -> LocationIntent | None:
    """Prefer the exact place the user attached to the task; otherwise infer from the title."""
    lat = getattr(task, "location_lat", None)
    lng = getattr(task, "location_lng", None)
    if lat is not None and lng is not None:
        return LocationIntent(
            query=getattr(task, "location_name", None) or task.title,
            requires_travel=True,
            coordinates=Coordinates(latitude=lat, longitude=lng),
        )
    return detect_location_intent(task.title)


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
        location_intent=_location_intent(task),
    )


async def _health(db: AsyncSession, user_id, now: datetime, tz: str = "UTC") -> HealthContext | None:
    from zoneinfo import ZoneInfo
    from app.repositories.daily_activity_repository import DailyActivityRepository

    ev = await SleepWakeRepository(db).get_latest_today(user_id)
    try:
        local_today = now.astimezone(ZoneInfo(tz)).date()
    except Exception:
        local_today = now.date()
    activity = await DailyActivityRepository(db).get_for_day(user_id, local_today)

    if ev is None and activity is None:
        return None

    # Sleep → energy/quality (default medium when we only have activity).
    sleep_hours = None
    energy, quality = "medium", None
    if ev is not None:
        if ev.sleep_start is not None:
            start = ev.sleep_start if ev.sleep_start.tzinfo else ev.sleep_start.replace(tzinfo=timezone.utc)
            wake = ev.wake_time if ev.wake_time.tzinfo else ev.wake_time.replace(tzinfo=timezone.utc)
            sleep_hours = round((wake - start).total_seconds() / 3600, 1)
        if sleep_hours is not None:
            if sleep_hours >= 7.5:
                energy, quality = "high", "good"
            elif sleep_hours >= 6:
                energy, quality = "medium", "okay"
            else:
                energy, quality = "low", "poor"

    steps = activity.steps if activity is not None else None
    return HealthContext(
        sleep_hours=sleep_hours, sleep_quality=quality, energy_estimate=energy,
        steps_today=steps,
        step_goal=10000 if steps is not None else None,
        sedentary_minutes=activity.inactive_minutes if activity is not None else None,
    )


_VALID_PLACE_TYPES = {
    "grocery_store", "pharmacy", "gym", "school", "office", "restaurant", "store",
    "gas_station", "walmart", "target", "costco", "custom",
}


def _to_place(row: UserPlace) -> Place:
    ptype = row.place_type if row.place_type in _VALID_PLACE_TYPES else "custom"
    return Place(
        id=str(row.id), name=row.name, type=ptype,  # type: ignore[arg-type]
        coordinates=Coordinates(latitude=row.latitude, longitude=row.longitude),
        source="user_saved", confidence=1.0, is_preferred=row.is_preferred,
    )


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
    health = await _health(db, user.id, now, tz)

    saved_rows = await UserPlaceRepository(db).list_for_user(user.id)
    preferred_places = [_to_place(r) for r in saved_rows]

    # Origin for travel = the coordinates of the saved place the user is currently at (we don't store
    # live GPS). If the current place isn't a saved place, we have no origin → errands stay unconfirmed.
    if location.place_name and location.coordinates is None:
        match = next((r for r in saved_rows
                      if r.name.casefold() == location.place_name.casefold()), None)
        if match is not None:
            location = dataclasses.replace(
                location, coordinates=Coordinates(latitude=match.latitude, longitude=match.longitude)
            )

    # Real calendar events synced from the device (EventKit). Timed events only — all-day events
    # aren't meetings to prep for or leave for, and would distort the free-block/next-event logic.
    event_rows = await SyncedCalendarEventRepository(db).list_window(
        user.id, now - timedelta(hours=1), now + timedelta(hours=24)
    )
    calendar_events = [
        CalendarEvent(
            id=e.external_id, title=e.title,
            start_time=(e.starts_at if e.starts_at.tzinfo else e.starts_at.replace(tzinfo=timezone.utc)).isoformat(),
            end_time=(e.ends_at if e.ends_at.tzinfo else e.ends_at.replace(tzinfo=timezone.utc)).isoformat(),
            location=e.location,
        )
        for e in event_rows if not e.all_day
    ]

    raw = RawContextInputs(
        now=now, timezone=tz, time_snapshot=snapshot,
        preferences=EngPreferences(
            work_hours=WorkHours(f"{work_start:02d}:00", f"{work_end:02d}:00"),
            default_travel_mode="driving",
            preferred_places=preferred_places,
        ),
        tasks=task_items, calendar_events=calendar_events, location_snapshot=location, health=health,
    )
    ctx = normalize_context(raw)
    # With no upcoming event, the free block is the usable-time window; otherwise keep the
    # event-derived free block (minutes until the next event).
    if ctx.calendar_context.next_event is None:
        ctx = dataclasses.replace(
            ctx,
            calendar_context=dataclasses.replace(
                ctx.calendar_context, free_block_minutes=usable_minutes
            ),
        )
    # Recently 'disagreed' tasks are demoted (not hidden) so a different rec surfaces.
    disagreed = await RecommendationFeedbackRepository(db).get_recently_disagreed_task_ids(user.id, now)
    if disagreed:
        ctx = dataclasses.replace(
            ctx, recently_disagreed_task_ids=frozenset(str(i) for i in disagreed)
        )
    return ctx, task_map
