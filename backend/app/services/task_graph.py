"""The read side of steps and prerequisites (TIME-320).

Every task that leaves the API goes through `TaskGraphService.responses`, so the graph fields
(`blocked_by`, step counts, `parent_title`) are never silently empty on one endpoint and filled on
another. `recommendable` is the single definition of "TimeSense may suggest this", shared by every
surface that picks a task.
"""
from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime, timezone
from dataclasses import dataclass, field

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.repositories.task_prerequisite_repository import MET_STATUSES, TaskPrerequisiteRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskRef, TaskResponse


@dataclass
class GraphInfo:
    blocked_by: dict[uuid.UUID, list[TaskRef]] = field(default_factory=dict)
    step_total: dict[uuid.UUID, int] = field(default_factory=dict)
    step_open: dict[uuid.UUID, int] = field(default_factory=dict)
    parents: dict[uuid.UUID, Task] = field(default_factory=dict)
    # For steps: their 1-based place among the group's live steps, and how many live steps there are.
    step_number: dict[uuid.UUID, int] = field(default_factory=dict)
    parent_step_count: dict[uuid.UUID, int] = field(default_factory=dict)

    def is_blocked(self, task_id: uuid.UUID) -> bool:
        return bool(self.blocked_by.get(task_id))

    def has_open_steps(self, task_id: uuid.UUID) -> bool:
        return self.step_open.get(task_id, 0) > 0

    def parent_of(self, task: Task) -> Task | None:
        return self.parents.get(task.parent_task_id) if task.parent_task_id else None


class TaskGraphService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.tasks = TaskRepository(db)
        self.edges = TaskPrerequisiteRepository(db)

    async def annotate(self, tasks: Iterable[Task]) -> GraphInfo:
        """Graph facts for a list of tasks in a fixed number of queries, however long the list:
        step counts, unmet prerequisites, and (only when some tasks are steps) their parents and their
        groups' steps."""
        tasks = list(tasks)
        if not tasks:
            return GraphInfo()
        by_id = {t.id: t for t in tasks}
        parent_ids = {t.parent_task_id for t in tasks if t.parent_task_id is not None}
        parents = {pid: by_id[pid] for pid in parent_ids if pid in by_id}
        missing = parent_ids - parents.keys()
        if missing:
            owners = {t.user_id for t in tasks}
            parents.update({p.id: p for p in await self.tasks.get_many(missing) if p.user_id in owners})

        counts = await self.tasks.step_counts(by_id.keys())
        unmet = await self.edges.unmet_for(set(by_id) | set(parents))
        # "STEP 2 OF 3" needs each step's live siblings (TIME-327).
        siblings = await self.tasks.steps_for(parents.keys()) if parents else {}

        info = GraphInfo(parents=parents)
        for t in tasks:
            info.step_total[t.id], info.step_open[t.id] = counts.get(t.id, (0, 0))
            waits = list(unmet.get(t.id, []))
            if t.parent_task_id in parents:
                # A step waits for whatever its whole group waits for: "Get photos" can't start before
                # the passport renewal itself is unblocked.
                seen = {prereq_id for prereq_id, _ in waits}
                waits += [w for w in unmet.get(t.parent_task_id, []) if w[0] not in seen]
                # A deleted step is no longer part of the group, so it counts for neither the number
                # nor the total.
                live = [s.id for s in siblings.get(t.parent_task_id, []) if s.status != "cancelled"]
                if t.id in live:
                    info.step_number[t.id] = live.index(t.id) + 1
                info.parent_step_count[t.id] = len(live)
            if waits:
                info.blocked_by[t.id] = [TaskRef(id=i, title=title) for i, title in waits]
        return info

    @staticmethod
    def recommendable(tasks: Iterable[Task], info: GraphInfo) -> list[Task]:
        """What TimeSense may suggest: nothing still waiting on another task, no parent whose steps are
        still open (the next step is suggested instead), and no step left over from a parent that was
        finished or deleted."""
        out = []
        for t in tasks:
            if info.is_blocked(t.id) or info.has_open_steps(t.id):
                continue
            parent = info.parent_of(t)
            if parent is not None and parent.status in MET_STATUSES:
                continue
            out.append(t)
        return out

    async def responses(
        self, tasks: Iterable[Task], info: GraphInfo | None = None
    ) -> list[TaskResponse]:
        tasks = list(tasks)
        if info is None:
            info = await self.annotate(tasks)
        # The graph queries autoflush whatever the request changed first (a backfilled estimate, a
        # status), and a flush expires server-set columns such as updated_at. Serializing would then
        # lazy-load them outside async IO and raise MissingGreenlet, so reload those rows here.
        for t in tasks:
            if inspect(t).expired_attributes:
                await self.db.refresh(t)
        return [self._response(t, info) for t in tasks]

    async def response(self, task: Task) -> TaskResponse:
        return (await self.responses([task]))[0]

    async def response_with_steps(self, parent: Task) -> TaskResponse:
        """The parent with its steps nested in order, annotated together in one pass. Cancelled steps
        are left out: a deleted step is no longer part of the group."""
        steps = [
            s for s in (await self.tasks.steps_for([parent.id])).get(parent.id, [])
            if s.status != "cancelled"
        ]
        payloads = await self.responses([parent, *steps])
        return payloads[0].model_copy(update={"steps": payloads[1:]})

    async def waits_until(self, task: Task) -> tuple[datetime | None, list[TaskRef]]:
        """When this task could start, as far as what it waits for is concerned (TIME-323).

        Returns the latest scheduled end among its unmet prerequisites, including those it inherits
        from its parent, together with the prerequisites that have no time at all. Nothing sensible can
        be scheduled after something untimed, so callers leave such a task unplaced."""
        waiting_ids = [task.id] + ([task.parent_task_id] if task.parent_task_id else [])
        unmet = await self.edges.unmet_for(waiting_ids)
        prerequisite_ids = {prereq_id for refs in unmet.values() for prereq_id, _ in refs}
        if not prerequisite_ids:
            return None, []
        latest: datetime | None = None
        untimed: list[TaskRef] = []
        for prereq in await self.tasks.get_many(prerequisite_ids, task.user_id):
            end = prereq.scheduled_end or prereq.scheduled_start
            if end is None:
                untimed.append(TaskRef(id=prereq.id, title=prereq.title))
                continue
            end = end if end.tzinfo else end.replace(tzinfo=timezone.utc)
            latest = end if latest is None or end > latest else latest
        return latest, untimed

    @staticmethod
    def _response(task: Task, info: GraphInfo) -> TaskResponse:
        parent = info.parent_of(task)
        return TaskResponse.model_validate(task).model_copy(
            update={
                "parent_title": parent.title if parent is not None else None,
                "step_number": info.step_number.get(task.id),
                "parent_step_count": info.parent_step_count.get(task.id, 0),
                "step_count": info.step_total.get(task.id, 0),
                "open_step_count": info.step_open.get(task.id, 0),
                "blocked_by": info.blocked_by.get(task.id, []),
            }
        )
