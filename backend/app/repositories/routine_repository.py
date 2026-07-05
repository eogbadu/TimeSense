from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.routine import DEFAULT_ROUTINES, RoutineAssumption


class RoutineAssumptionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_seed_defaults(self, user_id: uuid.UUID) -> list[RoutineAssumption]:
        result = await self.db.execute(
            select(RoutineAssumption).where(RoutineAssumption.user_id == user_id)
        )
        existing = list(result.scalars().all())
        if existing:
            return existing

        seeded = [
            RoutineAssumption(
                user_id=user_id,
                routine_type=routine_type,
                start_minute=start,
                end_minute=end,
            )
            for routine_type, (start, end) in DEFAULT_ROUTINES.items()
        ]
        self.db.add_all(seeded)
        await self.db.flush()
        for row in seeded:
            await self.db.refresh(row)
        return seeded

    async def get_one(self, user_id: uuid.UUID, routine_type: str) -> RoutineAssumption | None:
        result = await self.db.execute(
            select(RoutineAssumption).where(
                RoutineAssumption.user_id == user_id,
                RoutineAssumption.routine_type == routine_type,
            )
        )
        return result.scalar_one_or_none()

    async def update_one(
        self, user_id: uuid.UUID, routine_type: str, start_minute: int, end_minute: int
    ) -> RoutineAssumption | None:
        # Ensure defaults exist first so a PATCH on a never-fetched user still finds a row to update.
        await self.get_or_seed_defaults(user_id)
        routine = await self.get_one(user_id, routine_type)
        if routine is None:
            return None
        routine.start_minute = start_minute
        routine.end_minute = end_minute
        routine.is_customized = True
        await self.db.flush()
        await self.db.refresh(routine)
        return routine
