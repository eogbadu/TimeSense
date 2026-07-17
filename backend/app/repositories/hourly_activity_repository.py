from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hourly_activity import HourlyActivity


class HourlyActivityRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert(
        self, user_id: uuid.UUID, hour_start: datetime, steps: int, source: str = "healthkit"
    ) -> HourlyActivity:
        existing = (await self.db.execute(
            select(HourlyActivity).where(
                HourlyActivity.user_id == user_id,
                HourlyActivity.hour_start == hour_start,
            )
        )).scalar_one_or_none()
        if existing is not None:
            existing.steps = steps
            existing.source = source
            await self.db.flush()
            return existing
        row = HourlyActivity(user_id=user_id, hour_start=hour_start, steps=steps, source=source)
        self.db.add(row)
        await self.db.flush()
        return row

    async def list_in_range(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> list[HourlyActivity]:
        rows = await self.db.execute(
            select(HourlyActivity)
            .where(
                HourlyActivity.user_id == user_id,
                HourlyActivity.hour_start >= start,
                HourlyActivity.hour_start <= end,
            )
            .order_by(HourlyActivity.hour_start)
        )
        return list(rows.scalars().all())
