"""
Shared auto-placement for tasks that arrive from a source other than Capture (TIME-278).

Notion imports and confirmed email tasks used to land untimed — no duration, no slot — so they piled
up as to-dos instead of being planned in. This mirrors the Capture auto-placement: estimate a
duration if missing, then find the next open slot today (working hours), scheduling around existing
tasks AND calendar meetings. Read-only w.r.t. the calendar — it only sets the task's own time block.
Degrades gracefully: if nothing fits, the task simply stays untimed (its previous behavior).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.repositories.synced_calendar_event_repository import SyncedCalendarEventRepository
from app.repositories.task_repository import TaskRepository
from app.services.scheduling_service import SchedulingService
from app.services.task_duration_service import TaskDurationEstimator
from app.services.user_service import UserService


async def autoschedule_task(db: AsyncSession, task: Task, now: datetime | None = None) -> bool:
    """Place `task` into the next open slot today if it's untimed and due today (or undated).

    Estimates a duration first when the task has none. Returns True if the task was scheduled (its
    scheduled_start/end and auto_scheduled are set + flushed); False if it was left untimed.
    """
    now = now or datetime.now(timezone.utc)
    if task.scheduled_start is not None:
        return False

    if not task.estimated_minutes:
        minutes, _category = await TaskDurationEstimator(db).estimate(task.user_id, task.title)
        task.estimated_minutes = minutes
        await db.flush()
    if not task.estimated_minutes:
        return False

    today = now.date()
    due = task.due_at
    due_today_or_none = (
        due is None
        or (due if due.tzinfo else due.replace(tzinfo=timezone.utc)).date() == today
    )
    if not due_today_or_none:
        return False

    user = await UserService(db).get_by_id(task.user_id)
    if user is None:
        return False

    today_scheduled = await TaskRepository(db).list_by_user(user_id=task.user_id, for_date=today, limit=200)
    events = await SyncedCalendarEventRepository(db).list_window(task.user_id, now, now + timedelta(days=1))
    busy = list(today_scheduled) + [
        SimpleNamespace(scheduled_start=e.starts_at, scheduled_end=e.ends_at)
        for e in events if not e.all_day
    ]

    prefs = user.preferences
    scheduler = SchedulingService(
        work_start_hour=prefs.work_start_hour if prefs else 8,
        work_end_hour=prefs.work_end_hour if prefs else 21,
    )
    user_tz = user.profile.timezone if user.profile else "UTC"
    slot = scheduler.find_slot(now, task.estimated_minutes, busy, user_tz)
    if slot is None:
        return False

    task.scheduled_start = slot
    task.scheduled_end = slot + timedelta(minutes=task.estimated_minutes)
    task.auto_scheduled = True
    await db.flush()
    return True
