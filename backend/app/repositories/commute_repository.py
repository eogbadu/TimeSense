from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commute import CommuteEvent


class CommuteRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        direction: str,
        detected_start: datetime,
        detected_end: datetime,
        estimated_minutes: int,
        notification_id: uuid.UUID | None = None,
    ) -> CommuteEvent:
        event = CommuteEvent(
            user_id=user_id,
            direction=direction,
            detected_start=detected_start,
            detected_end=detected_end,
            estimated_minutes=estimated_minutes,
            notification_id=notification_id,
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def get(self, commute_id: uuid.UUID, user_id: uuid.UUID) -> CommuteEvent | None:
        result = await self.db.execute(
            select(CommuteEvent).where(
                CommuteEvent.id == commute_id, CommuteEvent.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_pending(self, user_id: uuid.UUID) -> list[CommuteEvent]:
        result = await self.db.execute(
            select(CommuteEvent)
            .where(CommuteEvent.user_id == user_id, CommuteEvent.status == "pending")
            .order_by(CommuteEvent.detected_start.desc())
        )
        return list(result.scalars().all())

    async def set_status(self, commute_id: uuid.UUID, user_id: uuid.UUID, status: str) -> bool:
        event = await self.get(commute_id, user_id)
        if event is None or event.status != "pending":
            return False
        event.status = status
        await self.db.flush()
        return True

    async def count_confirmed_in_range(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(CommuteEvent).where(
                CommuteEvent.user_id == user_id,
                CommuteEvent.status == "confirmed",
                CommuteEvent.detected_start >= start,
                CommuteEvent.detected_start < end,
            )
        )
        return result.scalar_one()

    async def sum_confirmed_minutes_in_range(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> int:
        """Total estimated minutes across confirmed commutes in the window (drives the driving/commute
        behavioral pattern). 0 when there are none."""
        result = await self.db.execute(
            select(func.coalesce(func.sum(CommuteEvent.estimated_minutes), 0)).where(
                CommuteEvent.user_id == user_id,
                CommuteEvent.status == "confirmed",
                CommuteEvent.detected_start >= start,
                CommuteEvent.detected_start < end,
            )
        )
        return int(result.scalar_one() or 0)
