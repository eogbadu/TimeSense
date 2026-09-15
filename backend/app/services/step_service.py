"""Steps: putting a task into a group, creating steps, and taking a task out again (TIME-321).

A task is standalone, a parent, or a step of exactly one parent — never deeper. Every way a task joins
a group goes through `attach`: a PATCH that moves it, a POST that creates steps, and later capture
("add get photos to renew passport") and the Notion import. What happens when a status changes (a
group finishing, or reopening) is not here: it lives in TaskRepository, because three code paths write
`done` straight through it.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.repositories.task_prerequisite_repository import TaskPrerequisiteRepository
from app.repositories.task_repository import OPEN_STATUSES, TaskRepository
from app.schemas.task import StepDraft
from app.services.task_autoschedule import autoschedule_task
from app.services.task_duration_service import TaskDurationEstimator

MAX_STEPS = 12
DEFAULT_PRIORITY = 3


class StepError(Exception):
    """A request the product rules refuse, carrying the HTTP status the API should answer with."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class StepService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.tasks = TaskRepository(db)
        self.edges = TaskPrerequisiteRepository(db)

    async def attach(self, task: Task, parent: Task, position: int | None = None) -> Task:
        """Make `task` a step of `parent`, or move it within that group if it is already there.

        Without a position the task goes last. Positions are renumbered so the group stays 0..n-1."""
        if parent.user_id != task.user_id:
            raise StepError(404, "Task not found.")
        if parent.id == task.id:
            raise StepError(400, "A task can't be a step of itself.")
        self.check_can_hold_steps(parent)
        if task.source == "calendar":
            raise StepError(422, "Calendar events can't be steps.")
        if await self._live_step_count(task.id) > 0:
            raise StepError(422, "A task that has its own steps can't become a step.")

        old_parent_id = task.parent_task_id
        joining = old_parent_id != parent.id
        if joining and await self._live_step_count(parent.id) >= MAX_STEPS:
            raise StepError(422, f"A task can have at most {MAX_STEPS} steps.")

        siblings = (await self.tasks.steps_for([parent.id])).get(parent.id, [])
        order = [s for s in siblings if s.id != task.id]
        index = len(order) if position is None else max(0, min(position, len(order)))
        order.insert(index, task)

        task.parent_task_id = parent.id
        if joining and task.priority == DEFAULT_PRIORITY:
            # A step of an urgent task is urgent. Only the default is replaced, never a priority
            # someone chose for this task.
            task.priority = parent.priority
        for i, step in enumerate(order):
            step.position = i
        await self.db.flush()

        await self.edges.rechain_steps(parent)
        if old_parent_id is not None and joining:
            await self._rechain(old_parent_id, task.user_id)
        await self._hand_slot_to_steps(parent)
        return task

    async def detach(self, task: Task) -> Task:
        """Take a step out of its group. It becomes a standalone task again."""
        old_parent_id = task.parent_task_id
        if old_parent_id is None:
            return task
        task.parent_task_id = None
        task.position = None
        await self.db.flush()
        await self._rechain(old_parent_id, task.user_id)
        return task

    async def create_steps(
        self, parent: Task, drafts: Sequence[StepDraft], sequential: bool | None = None
    ) -> list[Task]:
        """Create new tasks as steps of `parent`, after any it already has.

        `sequential` sets whether the group's steps happen in order. None keeps the current setting."""
        self.check_can_hold_steps(parent)
        if await self._live_step_count(parent.id) + len(drafts) > MAX_STEPS:
            raise StepError(422, f"A task can have at most {MAX_STEPS} steps.")
        if sequential is not None:
            parent.steps_sequential = sequential

        estimator = TaskDurationEstimator(self.db)
        position = await self.tasks.next_position(parent.id)
        created = []
        for draft in drafts:
            minutes = draft.estimated_minutes
            if minutes is None:
                minutes, _type = await estimator.estimate(parent.user_id, draft.title, None)
            created.append(
                await self.tasks.create(
                    user_id=parent.user_id,
                    title=draft.title,
                    estimated_minutes=minutes,
                    priority=parent.priority,
                    source=parent.source,
                    parent_task_id=parent.id,
                    position=position,
                )
            )
            position += 1

        await self.edges.rechain_steps(parent)
        await self._hand_slot_to_steps(parent)
        return created

    @staticmethod
    def check_can_hold_steps(parent: Task) -> None:
        if parent.parent_task_id is not None:
            raise StepError(422, "Steps can't have steps of their own.")
        if parent.status not in OPEN_STATUSES:
            raise StepError(422, "That task is already finished.")
        if parent.source == "calendar":
            raise StepError(422, "Calendar events can't have steps.")

    async def _live_step_count(self, task_id: uuid.UUID) -> int:
        return (await self.tasks.step_counts([task_id])).get(task_id, (0, 0))[0]

    async def _rechain(self, parent_id: uuid.UUID, user_id: uuid.UUID) -> None:
        parent = await self.tasks.get_by_id(parent_id, user_id)
        if parent is not None:
            await self.edges.rechain_steps(parent)

    async def _hand_slot_to_steps(self, parent: Task) -> None:
        """A time TimeSense chose for the whole task now goes to its first open step. Keeping both
        would book the same work twice. A time the user set is left exactly where it is."""
        if not parent.auto_scheduled or parent.scheduled_start is None:
            return
        parent.scheduled_start = None
        parent.scheduled_end = None
        parent.auto_scheduled = False
        await self.db.flush()
        steps = (await self.tasks.steps_for([parent.id])).get(parent.id, [])
        first = next((s for s in steps if s.status in OPEN_STATUSES), None)
        if first is not None and first.scheduled_start is None:
            await autoschedule_task(self.db, first)
