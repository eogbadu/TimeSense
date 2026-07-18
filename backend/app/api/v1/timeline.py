from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.repositories.synced_calendar_event_repository import SyncedCalendarEventRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("/today", response_model=list[TaskResponse])
async def get_today_timeline(
    current_user: CurrentUser,
    target_date: date | None = Query(default=None, alias="date", description="ISO date, defaults to today UTC"),
    db: AsyncSession = Depends(get_db),
) -> list[TaskResponse]:
    """Today's tasks: everything scheduled for the day, plus (when viewing today) untimed pending
    to-dos — e.g. just-captured tasks with no time — so the user sees their full list, not just
    scheduled blocks. Sorted by scheduled_start ascending (untimed tasks sort last)."""
    user_svc = UserService(db)
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")

    utc_today = datetime.now(timezone.utc).date()
    for_date = target_date or utc_today

    repo = TaskRepository(db)
    tasks = await repo.list_by_user(user_id=user.id, for_date=for_date, limit=200)

    # Include untimed pending to-dos (just-captured tasks with no time) when the user is viewing
    # "today". The client sends its LOCAL date, which can be a day off from the server's UTC date near
    # midnight, so accept any date within a day of UTC-today (the client only ever asks for its own
    # current date). Without this, late-evening users saw an empty "your day is open" screen.
    if abs((for_date - utc_today).days) <= 1:
        scheduled_ids = {t.id for t in tasks}
        all_pending = await repo.list_by_user(user_id=user.id, status="pending", limit=200)
        untimed = [t for t in all_pending if t.scheduled_start is None and t.id not in scheduled_ids]
        tasks = tasks + untimed

    tasks.sort(key=lambda t: t.scheduled_start or datetime.max.replace(tzinfo=timezone.utc))
    return [TaskResponse.model_validate(t) for t in tasks]


class TimelineEntry(BaseModel):
    """One row of the unified Smart Plan: either an actionable task or a read-only calendar meeting."""

    kind: Literal["task", "event"]
    id: str
    title: str
    start: datetime | None = None
    end: datetime | None = None
    source: str | None = None       # task.source or calendar event source
    location: str | None = None     # meetings only
    task: TaskResponse | None = None  # full task payload when kind == "task"


@router.get("/today/plan", response_model=list[TimelineEntry])
async def get_today_plan(
    current_user: CurrentUser,
    target_date: date | None = Query(default=None, alias="date", description="ISO date, defaults to today UTC"),
    db: AsyncSession = Depends(get_db),
) -> list[TimelineEntry]:
    """The unified Smart Plan for a day: actionable tasks woven together, in time order, with the
    user's calendar meetings as READ-ONLY busy blocks. Calendar-sourced tasks (from the legacy import)
    are excluded here — meetings appear once, as read-only events. All-day events are omitted."""
    user_svc = UserService(db)
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")

    utc_today = datetime.now(timezone.utc).date()
    for_date = target_date or utc_today

    repo = TaskRepository(db)
    # Exclude source="calendar" tasks: those meetings are shown as read-only event blocks instead, so
    # they aren't double-listed (and aren't presented as checkable to-dos).
    tasks = [t for t in await repo.list_by_user(user_id=user.id, for_date=for_date, limit=200)
             if t.source != "calendar"]

    if abs((for_date - utc_today).days) <= 1:
        scheduled_ids = {t.id for t in tasks}
        all_pending = await repo.list_by_user(user_id=user.id, status="pending", limit=200)
        tasks += [t for t in all_pending
                  if t.scheduled_start is None and t.id not in scheduled_ids and t.source != "calendar"]

    day_start = datetime.combine(for_date, time.min, tzinfo=timezone.utc)
    events = await SyncedCalendarEventRepository(db).list_window(user.id, day_start, day_start + timedelta(days=1))

    entries = [
        TimelineEntry(
            kind="task", id=str(t.id), title=t.title,
            start=t.scheduled_start, end=t.scheduled_end,
            source=t.source, task=TaskResponse.model_validate(t),
        )
        for t in tasks
    ] + [
        TimelineEntry(
            kind="event", id=f"{e.source}:{e.external_id}", title=e.title,
            start=e.starts_at, end=e.ends_at, source=e.source, location=e.location,
        )
        for e in events if not e.all_day
    ]

    # Time order; untimed to-dos (start=None) sort last.
    entries.sort(key=lambda x: x.start or datetime.max.replace(tzinfo=timezone.utc))
    return entries
