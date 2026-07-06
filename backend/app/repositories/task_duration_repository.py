from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task_duration import TaskDurationEstimate

# Weight given to a new observation when updating a learned estimate (exponential moving average).
_LEARN_ALPHA = 0.3
# How many real observations before a category's estimate is "confident" and we stop asking.
LEARNING_SAMPLE_TARGET = 5


class TaskDurationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_minutes(self, user_id: uuid.UUID, category: str) -> int | None:
        row = await self._get(user_id, category)
        return row.estimated_minutes if row else None

    async def learning_active(self, user_id: uuid.UUID, category: str) -> bool:
        """True while we still want real-duration feedback for this category (estimate not yet
        confident) — used to only prompt 'how long did that take?' during the learning period."""
        row = await self._get(user_id, category)
        return row is None or row.sample_count < LEARNING_SAMPLE_TARGET

    async def _get(self, user_id: uuid.UUID, category: str) -> TaskDurationEstimate | None:
        result = await self.db.execute(
            select(TaskDurationEstimate).where(
                TaskDurationEstimate.user_id == user_id,
                TaskDurationEstimate.category == category,
            )
        )
        return result.scalar_one_or_none()

    async def record_actual(
        self, user_id: uuid.UUID, category: str, actual_minutes: int
    ) -> TaskDurationEstimate:
        """Fold a real observed duration into the learned estimate via an EMA. Creates the row on
        first observation (seeded to the actual value)."""
        actual_minutes = max(1, int(actual_minutes))
        row = await self._get(user_id, category)
        if row is None:
            row = TaskDurationEstimate(
                user_id=user_id,
                category=category,
                estimated_minutes=actual_minutes,
                sample_count=1,
            )
            self.db.add(row)
        else:
            blended = row.estimated_minutes * (1 - _LEARN_ALPHA) + actual_minutes * _LEARN_ALPHA
            row.estimated_minutes = max(1, round(blended))
            row.sample_count += 1
        await self.db.flush()
        return row
