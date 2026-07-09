from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_activity import DailyActivity


class DailyActivityRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_for_day(self, user_id: uuid.UUID, day: date) -> DailyActivity | None:
        result = await self.db.execute(
            select(DailyActivity).where(
                DailyActivity.user_id == user_id, DailyActivity.day == day
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self, user_id: uuid.UUID, day: date, steps: int,
        active_energy_kcal: int | None, exercise_minutes: int | None,
        inactive_minutes: int | None = None, source: str = "healthkit",
    ) -> DailyActivity:
        existing = await self.get_for_day(user_id, day)
        if existing is not None:
            existing.steps = steps
            existing.active_energy_kcal = active_energy_kcal
            existing.exercise_minutes = exercise_minutes
            existing.inactive_minutes = inactive_minutes
            existing.source = source
            await self.db.flush()
            return existing
        row = DailyActivity(
            user_id=user_id, day=day, steps=steps,
            active_energy_kcal=active_energy_kcal, exercise_minutes=exercise_minutes,
            inactive_minutes=inactive_minutes, source=source,
        )
        self.db.add(row)
        await self.db.flush()
        return row
