from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insight import WeeklyInsight


class InsightRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_week(self, user_id: uuid.UUID, week_start: date) -> WeeklyInsight | None:
        result = await self.db.execute(
            select(WeeklyInsight).where(
                WeeklyInsight.user_id == user_id,
                WeeklyInsight.week_start == week_start,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: uuid.UUID, **fields) -> WeeklyInsight:
        insight = WeeklyInsight(user_id=user_id, **fields)
        self.db.add(insight)
        await self.db.flush()
        await self.db.refresh(insight)
        return insight

    async def list_recent(self, user_id: uuid.UUID, limit: int = 8) -> list[WeeklyInsight]:
        result = await self.db.execute(
            select(WeeklyInsight)
            .where(WeeklyInsight.user_id == user_id)
            .order_by(WeeklyInsight.week_start.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
