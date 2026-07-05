from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task


class TaskRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        title: str,
        **kwargs,
    ) -> Task:
        task = Task(user_id=user_id, title=title, **kwargs)
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def get_by_id(self, task_id: uuid.UUID, user_id: uuid.UUID) -> Task | None:
        result = await self.db.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        status: str | None = None,
        for_date: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Task]:
        q = select(Task).where(Task.user_id == user_id)
        if status:
            q = q.where(Task.status == status)
        if for_date:
            day_start = datetime(for_date.year, for_date.month, for_date.day, tzinfo=timezone.utc)
            day_end = datetime(for_date.year, for_date.month, for_date.day, 23, 59, 59, tzinfo=timezone.utc)
            q = q.where(
                and_(
                    Task.scheduled_start >= day_start,
                    Task.scheduled_start <= day_end,
                )
            )
        q = q.order_by(Task.scheduled_start.nulls_last(), Task.priority.asc()).limit(limit).offset(offset)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def update(self, task_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Task | None:
        task = await self.get_by_id(task_id, user_id)
        if task is None:
            return None
        for field, value in kwargs.items():
            if value is not None:
                setattr(task, field, value)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def soft_delete(self, task_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        task = await self.get_by_id(task_id, user_id)
        if task is None:
            return False
        task.status = "cancelled"
        await self.db.flush()
        return True

    async def count_created_in_range(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> int:
        """Tasks (excluding cancelled) created in [start, end) — a proxy for capture volume."""
        result = await self.db.execute(
            select(func.count()).select_from(Task).where(
                Task.user_id == user_id,
                Task.status != "cancelled",
                Task.created_at >= start,
                Task.created_at < end,
            )
        )
        return result.scalar_one()

    async def count_completed_in_range(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> int:
        """Tasks marked done with updated_at in [start, end) — a proxy for completions, since
        Task has no explicit completed_at field yet."""
        result = await self.db.execute(
            select(func.count()).select_from(Task).where(
                Task.user_id == user_id,
                Task.status == "done",
                Task.updated_at >= start,
                Task.updated_at < end,
            )
        )
        return result.scalar_one()
