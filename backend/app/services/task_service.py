from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = TaskRepository(db)

    async def create_task(
        self, user_id: uuid.UUID, body: TaskCreate, auto_scheduled: bool = False
    ) -> Task:
        return await self.repo.create(
            user_id=user_id,
            title=body.title,
            description=body.description,
            priority=body.priority,
            estimated_minutes=body.estimated_minutes,
            scheduled_start=body.scheduled_start,
            scheduled_end=body.scheduled_end,
            due_at=body.due_at,
            source=body.source,
            auto_scheduled=auto_scheduled,
            raw_input=body.raw_input,
        )

    async def get_task(self, task_id: uuid.UUID, user_id: uuid.UUID) -> Task | None:
        return await self.repo.get_by_id(task_id, user_id)

    async def list_tasks(
        self,
        user_id: uuid.UUID,
        status: str | None = None,
        for_date: date | None = None,
    ) -> list[Task]:
        return await self.repo.list_by_user(user_id, status=status, for_date=for_date)

    async def update_task(
        self, task_id: uuid.UUID, user_id: uuid.UUID, body: TaskUpdate
    ) -> Task | None:
        return await self.repo.update(
            task_id, user_id, **body.model_dump(exclude_none=True)
        )

    async def delete_task(self, task_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return await self.repo.soft_delete(task_id, user_id)
