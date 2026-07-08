from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.synced_calendar_event import SyncedCalendarEvent


class SyncedCalendarEventRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def replace_for_source(self, user_id: uuid.UUID, source: str, events: list[dict]) -> int:
        """Replace all of the user's synced events for a source (the app owns the source of truth)."""
        await self.db.execute(
            delete(SyncedCalendarEvent).where(
                and_(SyncedCalendarEvent.user_id == user_id, SyncedCalendarEvent.source == source)
            )
        )
        for e in events:
            self.db.add(SyncedCalendarEvent(
                user_id=user_id, source=source, external_id=e["external_id"], title=e["title"],
                starts_at=e["starts_at"], ends_at=e["ends_at"],
                location=e.get("location"), all_day=e.get("all_day", False),
            ))
        await self.db.flush()
        return len(events)

    async def list_window(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> list[SyncedCalendarEvent]:
        rows = await self.db.execute(
            select(SyncedCalendarEvent)
            .where(
                and_(
                    SyncedCalendarEvent.user_id == user_id,
                    SyncedCalendarEvent.ends_at >= start,
                    SyncedCalendarEvent.starts_at <= end,
                )
            )
            .order_by(SyncedCalendarEvent.starts_at)
        )
        return list(rows.scalars().all())
