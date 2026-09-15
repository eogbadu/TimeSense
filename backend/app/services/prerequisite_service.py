"""Prerequisites: "Do this after…" between any two tasks (TIME-322).

A manual wait is stored in the same `task_prerequisites` table that ordered steps write to, with
origin='manual', so the engine has a single rule: skip anything with an unfinished prerequisite.
Re-chaining a group only rewrites sequence edges, so a wait the user set survives any change to a
group's steps.

The one thing this service must never allow is a loop. If A waits for B and B waits for A, neither is
ever recommended again and nothing on screen explains why.
"""
from __future__ import annotations

import uuid
from collections import defaultdict, deque

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.repositories.task_prerequisite_repository import TaskPrerequisiteRepository
from app.repositories.task_repository import TaskRepository
from app.services.step_service import StepError

MAX_PREREQUISITES = 10


class PrerequisiteService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.tasks = TaskRepository(db)
        self.edges = TaskPrerequisiteRepository(db)

    async def add(
        self, user_id: uuid.UUID, task_id: uuid.UUID, prerequisite_task_id: uuid.UUID
    ) -> Task:
        """Make `task_id` wait for `prerequisite_task_id`. Adding a wait that already exists is a no-op."""
        if task_id == prerequisite_task_id:
            raise StepError(400, "A task can't wait for itself.")
        task = await self.tasks.get_by_id(task_id, user_id)
        prerequisite = await self.tasks.get_by_id(prerequisite_task_id, user_id)
        if task is None or prerequisite is None:
            raise StepError(404, "Task not found.")
        if "calendar" in (task.source, prerequisite.source):
            raise StepError(422, "Calendar events can't wait for tasks or be waited on.")
        if task.parent_task_id == prerequisite.id:
            # The parent only finishes when its steps do, so a step waiting for it would wait forever.
            raise StepError(422, "A step can't wait for the task it belongs to.")
        if await self.edges.get(task.id, prerequisite.id) is not None:
            return task

        edges = await self.edges.edges_for_user(user_id)
        if sum(1 for waiting, _ in edges if waiting == task.id) >= MAX_PREREQUISITES:
            raise StepError(422, f"A task can wait for at most {MAX_PREREQUISITES} others.")
        parents = await self.tasks.parent_links(user_id)
        if self._would_loop(edges, parents, task.id, prerequisite.id):
            raise StepError(409, "That would make these tasks wait on each other.")

        await self.edges.add(user_id, task.id, prerequisite.id, origin="manual")
        return task

    async def remove(
        self, user_id: uuid.UUID, task_id: uuid.UUID, prerequisite_task_id: uuid.UUID
    ) -> None:
        """Stop `task_id` waiting for `prerequisite_task_id` ("Don't wait")."""
        task = await self.tasks.get_by_id(task_id, user_id)
        edge = await self.edges.get(task_id, prerequisite_task_id) if task is not None else None
        if edge is None:
            raise StepError(404, "Task not found.")
        if edge.origin == "sequence":
            # Re-chaining would put this wait straight back. The order belongs to the group, so it is
            # changed there instead.
            raise StepError(422, "This comes from the order of the task's steps.")
        await self.edges.remove(task_id, prerequisite_task_id)

    @staticmethod
    def _would_loop(
        edges: list[tuple[uuid.UUID, uuid.UUID]],
        parents: dict[uuid.UUID, uuid.UUID],
        task_id: uuid.UUID,
        prerequisite_id: uuid.UUID,
    ) -> bool:
        """Would "task waits for prerequisite" close a loop?

        It would if the prerequisite already waits, directly or through a chain, for the task. A step
        also waits for whatever its parent waits for, so that inherited wait counts as a link too.
        Without it, "Renew passport waits for its own step Get photos" would pass this check and then
        block that step forever."""
        waits_for: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
        for waiting, prereq in edges:
            waits_for[waiting].append(prereq)
        for step, parent in parents.items():
            waits_for[step].append(parent)

        seen = {prerequisite_id}
        queue = deque([prerequisite_id])
        while queue:
            current = queue.popleft()
            if current == task_id:
                return True
            for nxt in waits_for.get(current, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return False
