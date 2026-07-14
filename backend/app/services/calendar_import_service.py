"""
Import synced calendar events into the task list as real, editable tasks.

Each non-all-day event in the window becomes a Task (title, scheduled_start/end from the event,
source="calendar", location from the event). Deduped on calendar_event_id = "{source}:{external_id}"
against ALL of the user's tasks (incl. deleted) so a re-sync/re-import never duplicates, and a task
the user deleted doesn't come back.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.repositories.synced_calendar_event_repository import SyncedCalendarEventRepository
from app.repositories.task_repository import TaskRepository


class CalendarImportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.events = SyncedCalendarEventRepository(db)
        self.tasks = TaskRepository(db)

    async def import_window(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> list[Task]:
        events = await self.events.list_window(user_id, start, end)
        candidates = [e for e in events if not e.all_day]   # all-day events aren't actionable tasks
        keys = [f"{e.source}:{e.external_id}" for e in candidates]
        existing = await self.tasks.existing_calendar_event_ids(user_id, keys)

        created: list[Task] = []
        for e in candidates:
            key = f"{e.source}:{e.external_id}"
            if key in existing:
                continue
            minutes = max(1, int((e.ends_at - e.starts_at).total_seconds() // 60)) or None
            task = await self.tasks.create(
                user_id=user_id,
                title=e.title,
                scheduled_start=e.starts_at,
                scheduled_end=e.ends_at,
                estimated_minutes=minutes,
                source="calendar",
                calendar_event_id=key,
                location_name=e.location,
            )
            existing.add(key)   # guard against duplicate events within the same batch
            created.append(task)
        return created
