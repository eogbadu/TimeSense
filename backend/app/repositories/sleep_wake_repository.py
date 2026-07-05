from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sleep_wake import SleepWakeEvent


class SleepWakeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        wake_time: datetime,
        sleep_start: datetime | None = None,
        source: str = "manual",
    ) -> SleepWakeEvent:
        event = SleepWakeEvent(
            user_id=user_id,
            wake_time=wake_time,
            sleep_start=sleep_start,
            source=source,
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def set_replan_request(
        self, event_id: uuid.UUID, replan_request_id: uuid.UUID
    ) -> None:
        result = await self.db.execute(
            select(SleepWakeEvent).where(SleepWakeEvent.id == event_id)
        )
        event = result.scalar_one_or_none()
        if event:
            event.replan_request_id = replan_request_id
            await self.db.flush()

    async def has_replan_on_date(self, user_id: uuid.UUID, day: date) -> bool:
        """Whether a wake event on this UTC calendar date already triggered a replan."""
        result = await self.db.execute(
            select(SleepWakeEvent).where(
                SleepWakeEvent.user_id == user_id,
                SleepWakeEvent.replan_request_id.is_not(None),
            )
        )
        events = result.scalars().all()
        return any(_utc(e.wake_time).date() == day for e in events)

    async def count_late_wakes_in_range(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> int:
        """Wake events that triggered a morning replan (replan_request_id set) in [start, end)."""
        result = await self.db.execute(
            select(func.count()).select_from(SleepWakeEvent).where(
                SleepWakeEvent.user_id == user_id,
                SleepWakeEvent.replan_request_id.is_not(None),
                SleepWakeEvent.wake_time >= start,
                SleepWakeEvent.wake_time < end,
            )
        )
        return result.scalar_one()

    async def get_latest_today(self, user_id: uuid.UUID) -> SleepWakeEvent | None:
        today = datetime.now(timezone.utc).date()
        result = await self.db.execute(
            select(SleepWakeEvent)
            .where(SleepWakeEvent.user_id == user_id)
            .order_by(SleepWakeEvent.wake_time.desc())
        )
        for event in result.scalars().all():
            if _utc(event.wake_time).date() == today:
                return event
        return None


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
