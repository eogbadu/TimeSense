from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.task_duration_repository import TaskDurationRepository
from app.services.task_duration import infer_category, seed_duration


class TaskDurationEstimator:
    """Estimates how long a task will take: the user's learned per-category estimate when we have
    one, otherwise the seed lookup table. This is the assistant's sense of time, and it gets more
    accurate as record_actual folds in real observations."""

    def __init__(self, db: AsyncSession) -> None:
        self._repo = TaskDurationRepository(db)

    async def estimate(self, user_id: uuid.UUID, title: str) -> tuple[int, str]:
        """Return (estimated_minutes, category) for a task title."""
        category = infer_category(title)
        learned = await self._repo.get_minutes(user_id, category)
        return (learned if learned is not None else seed_duration(category)), category

    async def record_actual(self, user_id: uuid.UUID, title: str, actual_minutes: int) -> None:
        """Teach the estimator how long a task actually took (by its inferred category)."""
        await self._repo.record_actual(user_id, infer_category(title), actual_minutes)
