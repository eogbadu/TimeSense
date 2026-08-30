from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.implicit_deadline import repair_midnight


class TaskService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = TaskRepository(db)

    async def create_task(
        self,
        user_id: uuid.UUID,
        body: TaskCreate,
        auto_scheduled: bool = False,
        user_timezone: str = "UTC",
    ) -> Task:
        return await self.repo.create(
            user_id=user_id,
            title=body.title,
            description=body.description,
            priority=body.priority,
            estimated_minutes=body.estimated_minutes,
            scheduled_start=body.scheduled_start,
            scheduled_end=body.scheduled_end,
            # A date-only deadline arrives as local midnight — the instant the day BEGINS — so the
            # task is overdue for the entire day it was meant to be done in. Repaired here rather
            # than in capture so every client is covered, including the iOS picker that produced it
            # by calling Calendar.startOfDay (TIME-313).
            due_at=repair_midnight(body.due_at, user_timezone),
            source=body.source,
            auto_scheduled=auto_scheduled,
            raw_input=body.raw_input,
            location_name=body.location_name,
            location_lat=body.location_lat,
            location_lng=body.location_lng,
            task_type=body.task_type,
            difficulty=body.difficulty,
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
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        body: TaskUpdate,
        user_timezone: str = "UTC",
    ) -> Task | None:
        fields = body.model_dump(exclude_none=True)
        # Rescheduling a stale task (TIME-309) goes through here, so the same midnight repair has to
        # apply — otherwise "give it a new date of tomorrow" produces a deadline that is already
        # past for all of tomorrow.
        if "due_at" in fields:
            fields["due_at"] = repair_midnight(fields["due_at"], user_timezone)
        return await self.repo.update(task_id, user_id, **fields)

    async def delete_task(self, task_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return await self.repo.soft_delete(task_id, user_id)
