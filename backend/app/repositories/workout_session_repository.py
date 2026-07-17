from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workout_session import WorkoutSession


class WorkoutSessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert(
        self, user_id: uuid.UUID, external_id: str, workout_type: str,
        started_at: datetime, ended_at: datetime, duration_minutes: int,
        distance_meters: float | None = None, active_energy_kcal: int | None = None,
        source: str = "healthkit",
    ) -> WorkoutSession:
        existing = (await self.db.execute(
            select(WorkoutSession).where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.external_id == external_id,
            )
        )).scalar_one_or_none()
        if existing is not None:
            existing.workout_type = workout_type
            existing.started_at = started_at
            existing.ended_at = ended_at
            existing.duration_minutes = duration_minutes
            existing.distance_meters = distance_meters
            existing.active_energy_kcal = active_energy_kcal
            existing.source = source
            await self.db.flush()
            return existing
        row = WorkoutSession(
            user_id=user_id, external_id=external_id, workout_type=workout_type,
            started_at=started_at, ended_at=ended_at, duration_minutes=duration_minutes,
            distance_meters=distance_meters, active_energy_kcal=active_energy_kcal, source=source,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def list_in_range(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> list[WorkoutSession]:
        rows = await self.db.execute(
            select(WorkoutSession)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.started_at >= start,
                WorkoutSession.started_at <= end,
            )
            .order_by(WorkoutSession.started_at)
        )
        return list(rows.scalars().all())
