from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.energy_checkin import EnergyCheckIn

# How long a self-report stands. Long enough to be worth giving, short enough that it can't keep
# steering recommendations after the user's state has plainly moved on.
CHECKIN_VALID_FOR = timedelta(hours=4)


class EnergyCheckInRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        reported: str,
        inferred: str | None = None,
        inferred_score: float | None = None,
        reported_at: datetime | None = None,
    ) -> EnergyCheckIn:
        row = EnergyCheckIn(
            user_id=user_id,
            reported=reported,
            inferred=inferred,
            inferred_score=None if inferred_score is None else int(round(inferred_score * 100)),
            reported_at=reported_at or datetime.now(timezone.utc),
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def latest_valid(
        self, user_id: uuid.UUID, now: datetime | None = None
    ) -> EnergyCheckIn | None:
        """The most recent check-in still inside its window, or None."""
        now = now or datetime.now(timezone.utc)
        result = await self.db.execute(
            select(EnergyCheckIn)
            .where(
                EnergyCheckIn.user_id == user_id,
                EnergyCheckIn.reported_at > now - CHECKIN_VALID_FOR,
                EnergyCheckIn.reported_at <= now,
            )
            .order_by(EnergyCheckIn.reported_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_recent(
        self, user_id: uuid.UUID, limit: int = 100
    ) -> list[EnergyCheckIn]:
        """Reported-vs-inferred pairs, newest first — the calibration input."""
        result = await self.db.execute(
            select(EnergyCheckIn)
            .where(EnergyCheckIn.user_id == user_id)
            .order_by(EnergyCheckIn.reported_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
