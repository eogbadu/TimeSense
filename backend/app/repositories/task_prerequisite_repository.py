from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.task import Task, TaskPrerequisite

# A prerequisite stops blocking once it is finished OR abandoned: a deleted (cancelled) task must not
# hold its dependents hostage forever. `in_progress` still blocks (TIME-320).
MET_STATUSES = ("done", "cancelled")


class TaskPrerequisiteRepository:
    """Edges meaning "task_id waits for prerequisite_task_id" (TIME-320).

    Reads are bulk on purpose: Today and Now annotate whole lists, and a per-task query would multiply
    with the length of the day."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def unmet_for(
        self, task_ids: Iterable[uuid.UUID]
    ) -> dict[uuid.UUID, list[tuple[uuid.UUID, str]]]:
        """For each task, the (id, title) of every prerequisite not yet done or cancelled. One query."""
        ids = list(set(task_ids))
        if not ids:
            return {}
        prereq = aliased(Task)
        result = await self.db.execute(
            select(TaskPrerequisite.task_id, prereq.id, prereq.title)
            .join(prereq, prereq.id == TaskPrerequisite.prerequisite_task_id)
            .where(TaskPrerequisite.task_id.in_(ids), prereq.status.not_in(MET_STATUSES))
            .order_by(prereq.created_at)
        )
        unmet: dict[uuid.UUID, list[tuple[uuid.UUID, str]]] = {}
        for task_id, prereq_id, title in result.all():
            unmet.setdefault(task_id, []).append((prereq_id, title))
        return unmet

    async def edges_for_user(self, user_id: uuid.UUID) -> list[tuple[uuid.UUID, uuid.UUID]]:
        """Every (task_id, prerequisite_task_id) the user has, for walking the graph in memory."""
        result = await self.db.execute(
            select(TaskPrerequisite.task_id, TaskPrerequisite.prerequisite_task_id).where(
                TaskPrerequisite.user_id == user_id
            )
        )
        return [(task_id, prereq_id) for task_id, prereq_id in result.all()]

    async def get(
        self, task_id: uuid.UUID, prerequisite_task_id: uuid.UUID
    ) -> TaskPrerequisite | None:
        result = await self.db.execute(
            select(TaskPrerequisite).where(
                TaskPrerequisite.task_id == task_id,
                TaskPrerequisite.prerequisite_task_id == prerequisite_task_id,
            )
        )
        return result.scalar_one_or_none()

    async def add(
        self,
        user_id: uuid.UUID,
        task_id: uuid.UUID,
        prerequisite_task_id: uuid.UUID,
        origin: str = "manual",
    ) -> bool:
        """Idempotent. Returns False when the edge already exists, whatever its origin."""
        if await self.get(task_id, prerequisite_task_id) is not None:
            return False
        self.db.add(
            TaskPrerequisite(
                task_id=task_id,
                prerequisite_task_id=prerequisite_task_id,
                user_id=user_id,
                origin=origin,
            )
        )
        await self.db.flush()
        return True

    async def remove(self, task_id: uuid.UUID, prerequisite_task_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            delete(TaskPrerequisite)
            .where(
                TaskPrerequisite.task_id == task_id,
                TaskPrerequisite.prerequisite_task_id == prerequisite_task_id,
            )
            .execution_options(synchronize_session="fetch")
        )
        return (result.rowcount or 0) > 0

    async def rechain_steps(self, parent: Task) -> None:
        """Rewrite a group's automatic ordering.

        Drops every sequence edge touching the group's steps, including one still pointing at a step
        that has just moved out, then chains the remaining non-cancelled steps in position order if the
        group is ordered. Manual edges are never touched: the user set those. Without this, cancelling
        step 2 of 3 would unblock step 3 while step 1 is still open."""
        children = (
            await self.db.execute(
                select(Task)
                .where(Task.parent_task_id == parent.id)
                .order_by(Task.position.nulls_last(), Task.created_at)
            )
        ).scalars().all()
        child_ids = [c.id for c in children]
        if child_ids:
            await self.db.execute(
                delete(TaskPrerequisite)
                .where(
                    TaskPrerequisite.origin == "sequence",
                    or_(
                        TaskPrerequisite.task_id.in_(child_ids),
                        TaskPrerequisite.prerequisite_task_id.in_(child_ids),
                    ),
                )
                .execution_options(synchronize_session="fetch")
            )
        if parent.steps_sequential:
            live = [c for c in children if c.status != "cancelled"]
            for before, after in zip(live, live[1:]):
                await self.add(parent.user_id, after.id, before.id, origin="sequence")
        await self.db.flush()
