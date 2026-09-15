from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.user import User
from app.repositories.task_repository import TaskRepository
from app.schemas.task import StepDraft, TaskCreate, TaskUpdate
from app.services.implicit_deadline import repair_midnight
from app.services.step_service import StepError, StepService
from app.services.task_backfill import TaskBackfillService
from app.services.task_completion_service import TaskCompletionService


class TaskService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = TaskRepository(db)
        self.backfill = TaskBackfillService(db)
        self.completion = TaskCompletionService(db)
        self.steps = StepService(db)

    async def create_task(
        self,
        user_id: uuid.UUID,
        body: TaskCreate,
        auto_scheduled: bool = False,
        user_timezone: str = "UTC",
    ) -> Task:
        """Raises StepError when the group asked for is refused (TIME-321)."""
        parent = None
        if body.parent_task_id is not None:
            parent = await self.repo.get_by_id(body.parent_task_id, user_id)
            if parent is None:
                raise StepError(404, "Task not found.")
            # Checked before creating, so a refused group leaves no stray task behind.
            StepService.check_can_hold_steps(parent)

        task = await self.repo.create(
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
        if parent is not None:
            await self.steps.attach(task, parent)
        if body.steps:
            await self.steps.create_steps(task, body.steps, sequential=body.steps_sequential)
        return task

    async def add_steps(
        self, parent: Task, drafts: Sequence[StepDraft], sequential: bool | None = None
    ) -> list[Task]:
        return await self.steps.create_steps(parent, drafts, sequential=sequential)

    async def get_task(self, task_id: uuid.UUID, user_id: uuid.UUID) -> Task | None:
        task = await self.repo.get_by_id(task_id, user_id)
        if task is not None:
            await self.backfill.backfill(user_id, [task])
        return task

    async def list_tasks(
        self,
        user_id: uuid.UUID,
        status: str | None = None,
        for_date: date | None = None,
    ) -> list[Task]:
        tasks = await self.repo.list_by_user(user_id, status=status, for_date=for_date)
        # Rows captured before classification existed still carry pre-TIME-286 estimates — including
        # the values from the "everything takes 23 minutes" bug. Reading is where they get corrected
        # (TIME-311); nothing rewrites them in bulk.
        return await self.backfill.backfill(user_id, tasks)

    async def update_task(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        body: TaskUpdate,
        user_timezone: str = "UTC",
        user: User | None = None,
    ) -> Task | None:
        """`user` is needed only to learn from a completion (TIME-316); without it the task still
        updates exactly as before, just silently. Raises StepError when a group move is refused."""
        fields = body.model_dump(exclude_none=True)
        # Joining or leaving a group is not a plain column write: it is validated and the group's
        # ordering is rebuilt. An explicit null means "take it out of its group", which exclude_none
        # would hide, so the fields actually sent are read instead (TIME-321).
        moves_group = "parent_task_id" in body.model_fields_set
        new_parent_id = fields.pop("parent_task_id", None)
        position = fields.pop("position", None)
        # Rescheduling a stale task (TIME-309) goes through here, so the same midnight repair has to
        # apply — otherwise "give it a new date of tomorrow" produces a deadline that is already
        # past for all of tomorrow.
        if "due_at" in fields:
            fields["due_at"] = repair_midnight(fields["due_at"], user_timezone)

        # The prior status has to be read here: repo.update() loads the row itself and returns only
        # the result, and comparing against body.status would misread a re-sent "done" as a fresh
        # completion (Today's circle tap does exactly that).
        before = await self.repo.get_by_id(task_id, user_id)
        was_done = before is not None and before.status == "done"

        task = await self.repo.update(task_id, user_id, **fields)

        if task is not None and (moves_group or position is not None):
            await self._move(task, new_parent_id if moves_group else task.parent_task_id, position)

        # Only the task the user finished is learned from. A parent that finishes because its last
        # step did is closed inside the repository and never reaches this line.
        if task is not None and user is not None and not was_done and task.status == "done":
            await self.completion.record_completion(user, task)
        return task

    async def delete_task(self, task_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return await self.repo.soft_delete(task_id, user_id)

    async def _move(self, task: Task, parent_id: uuid.UUID | None, position: int | None) -> None:
        if parent_id is None:
            await self.steps.detach(task)
            return
        parent = await self.repo.get_by_id(parent_id, task.user_id)
        if parent is None:
            raise StepError(404, "Task not found.")
        await self.steps.attach(task, parent, position)
