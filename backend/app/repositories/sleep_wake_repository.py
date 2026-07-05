from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
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
        source: str = "healthkit",
    ) -> SleepWakeEvent:
        event = SleepWakeEvent(
            user_id=user_id,
            sleep_start=sleep_start,
            wake_time=wake_time,
            source=source,
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def get_latest_for_today(
        self, user_id: uuid.UUID, now: datetime | None = None
    ) -> SleepWakeEvent | None:
        now = now or datetime.now(timezone.utc)
        day_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        result = await self.db.execute(
            select(SleepWakeEvent)
            .where(
                SleepWakeEvent.user_id == user_id,
                SleepWakeEvent.wake_time >= day_start,
                SleepWakeEvent.wake_time < day_end,
            )
            .order_by(SleepWakeEvent.wake_time.desc())
        )
        return result.scalars().first()
