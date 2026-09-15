from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.localtime import local_day_bounds
from app.services.task_library import resolve_classification
from app.models.task import Task
from app.repositories.recommendation_swap_repository import RecommendationSwapRepository
from app.repositories.task_prerequisite_repository import TaskPrerequisiteRepository

# Still to do. No client sets `in_progress` today, but every reader treats it as open.
OPEN_STATUSES = ("pending", "in_progress")


class TaskRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        title: str,
        **kwargs,
    ) -> Task:
        # Classify here rather than at each call site: tasks are created from capture, manual entry,
        # and the Notion/email/Slack/Teams/calendar imports, and a path that forgot would silently
        # produce unclassified rows that fall back to the catch-all forever (TIME-285).
        # An explicit value always wins — the caller may have a better answer (e.g. the LLM's, or a
        # user correcting a wrong guess).
        if not kwargs.get("task_type") or not kwargs.get("difficulty"):
            inferred_type, inferred_difficulty = resolve_classification(
                title, kwargs.get("task_type"), kwargs.get("difficulty")
            )
            kwargs["task_type"] = kwargs.get("task_type") or inferred_type
            kwargs["difficulty"] = kwargs.get("difficulty") or inferred_difficulty

        task = Task(user_id=user_id, title=title, **kwargs)
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def existing_calendar_event_ids(
        self, user_id: uuid.UUID, keys: list[str]
    ) -> set[str]:
        """Which of `keys` already have a task for this user (any status, so a deleted import isn't
        resurrected) — used to dedup calendar-event imports."""
        if not keys:
            return set()
        result = await self.db.execute(
            select(Task.calendar_event_id).where(
                Task.user_id == user_id, Task.calendar_event_id.in_(keys)
            )
        )
        return {row[0] for row in result.all()}

    async def find_recent_duplicate(
        self, user_id: uuid.UUID, raw_input: str, since: datetime
    ) -> Task | None:
        """The most recent still-active capture with the same text (case-insensitive) created at or
        after `since` — used to make rapid double-taps / retries idempotent."""
        result = await self.db.execute(
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.source == "capture",
                Task.status.in_(("pending", "in_progress")),
                func.lower(Task.raw_input) == raw_input.strip().lower(),
                Task.created_at >= since,
            )
            .order_by(Task.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

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
        user_timezone: str | None = None,
    ) -> list[Task]:
        q = select(Task).where(Task.user_id == user_id)
        if status:
            q = q.where(Task.status == status)
        if for_date:
            # The user's LOCAL day, not the UTC day — a Tokyo user's "today" starts at 15:00 UTC the
            # previous date. Half-open so nothing in the final second of the day is dropped.
            day_start, day_end = local_day_bounds(for_date, user_timezone)
            q = q.where(
                and_(
                    Task.scheduled_start >= day_start,
                    Task.scheduled_start < day_end,
                )
            )
        q = q.order_by(Task.scheduled_start.nulls_last(), Task.priority.asc()).limit(limit).offset(offset)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def upcoming_appointments(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> list[Task]:
        """Timed appointments starting in (start, end] that aren't done/cancelled — the input to the
        appointment-reminder scheduler (TIME-251)."""
        q = (
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.scheduled_start.is_not(None),
                Task.scheduled_start > start,
                Task.scheduled_start <= end,
                Task.status.not_in(["done", "cancelled"]),
            )
            .order_by(Task.scheduled_start)
        )
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def upcoming_commitments(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> list[Task]:
        """The user's next commitments in (start, end] — tasks with a scheduled_start OR a due_at in the
        window (not done/cancelled). Unlike upcoming_appointments this also counts due-only tasks
        (email/Notion/manually added), so the Why-sheet Calendar signal can name the real next thing
        rather than defaulting to end-of-workday (TIME-265)."""
        q = (
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.status.not_in(["done", "cancelled"]),
                or_(
                    and_(Task.scheduled_start.is_not(None),
                         Task.scheduled_start > start, Task.scheduled_start <= end),
                    and_(Task.due_at.is_not(None), Task.due_at > start, Task.due_at <= end),
                ),
            )
            .order_by(Task.scheduled_start.nulls_last(), Task.due_at)
        )
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def update(self, task_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Task | None:
        task = await self.get_by_id(task_id, user_id)
        if task is None:
            return None
        old_status = task.status
        was_done = old_status == "done"
        for field, value in kwargs.items():
            if value is not None:
                setattr(task, field, value)
        # Stamp the completion instant on the pending→done EDGE only (TIME-316). Re-saving a done
        # task, or editing its title a week later, must not move it — that is precisely the
        # lossiness that made `updated_at` an unusable proxy. This lives in the repository rather
        # than the service because `POST /recommendations/feedback` calls update() directly.
        if task.status == "done" and not was_done and task.completed_at is None:
            task.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self._settle_graph(task, old_status)
        await self.db.refresh(task)
        return task

    async def soft_delete(self, task_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        task = await self.get_by_id(task_id, user_id)
        if task is None:
            return False
        old_status = task.status
        task.status = "cancelled"
        await self.db.flush()
        await self._settle_graph(task, old_status)
        return True

    async def _settle_graph(self, task: Task, old_status: str) -> None:
        """Keep a group consistent after a status change (TIME-321).

        This lives here rather than in TaskService for the same reason the completed_at stamp does:
        three paths write `done` straight through this repository (TaskService, POST
        /recommendations/feedback and the Google Assistant webhook), and soft delete writes
        `cancelled`. A rule enforced one layer up would silently not apply to two of them.
        """
        if task.status == old_status:
            return
        now = datetime.now(timezone.utc)

        if task.parent_task_id is not None:
            parent = await self.get_by_id(task.parent_task_id, task.user_id)
            if parent is None:
                return
            if task.status == "cancelled":
                # Close the gap, or cancelling step 2 of 3 would unblock step 3 while step 1 is open.
                await TaskPrerequisiteRepository(self.db).rechain_steps(parent)
            live, still_open = (await self.step_counts([parent.id])).get(parent.id, (0, 0))
            if still_open == 0 and live > 0 and parent.status in OPEN_STATUSES:
                # The parent only held its steps, so finishing the last one finishes it. There is no
                # prompt, and nothing is learned from it: the user finished steps, not another task.
                parent.status = "done"
                parent.completed_at = parent.completed_at or now
            elif still_open > 0 and parent.status == "done":
                parent.status = "pending"
                parent.completed_at = None  # set directly: update() skips None values
        elif task.status in ("done", "cancelled"):
            closed = []
            for step in (await self.steps_for([task.id])).get(task.id, []):
                if step.status in OPEN_STATUSES:
                    step.status = task.status
                    if task.status == "done":
                        step.completed_at = now
                    closed.append(step.id)
            # A pin on a step that just closed would keep recommending finished work for hours.
            swaps = RecommendationSwapRepository(self.db)
            for step_id in closed:
                await swaps.release_pin(task.user_id, step_id)
        await self.db.flush()

    async def count_created_in_range(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> int:
        """Tasks (excluding cancelled) created in [start, end) — a proxy for capture volume.

        Steps are left out: breaking one task into five is not five captures (TIME-321)."""
        result = await self.db.execute(
            select(func.count()).select_from(Task).where(
                Task.user_id == user_id,
                Task.status != "cancelled",
                Task.parent_task_id.is_(None),
                Task.created_at >= start,
                Task.created_at < end,
            )
        )
        return result.scalar_one()

    async def count_completed_in_range(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> int:
        """Tasks completed in [start, end).

        Uses the real `completed_at` where it exists and falls back to `updated_at` for rows
        finished before that column did (TIME-316), so historic counts keep working while new ones
        stop drifting every time a done task is edited.

        A parent with steps is not counted. Its steps are the work, and counting the parent as well
        would credit the same work twice when the group finishes by itself (TIME-321)."""
        completed = func.coalesce(Task.completed_at, Task.updated_at)
        step = aliased(Task)
        has_steps = (
            select(step.id)
            .where(step.parent_task_id == Task.id, step.status != "cancelled")
            .exists()
        )
        result = await self.db.execute(
            select(func.count()).select_from(Task).where(
                Task.user_id == user_id,
                Task.status == "done",
                ~has_steps,
                completed >= start,
                completed < end,
            )
        )
        return result.scalar_one()

    async def completion_of_added_in_range(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> tuple[int, int]:
        """Of the tasks added in [start, end): how many there are, and how many of those are done.

        Both numbers count the same tasks, so done can never exceed total. Mixing "finished this
        week" with "added this week" let a week report 7 of 4 (TIME-330). Steps count as tasks and a
        parent with live steps does not, the same rule as `count_completed_in_range`."""
        step = aliased(Task)
        has_steps = (
            select(step.id)
            .where(step.parent_task_id == Task.id, step.status != "cancelled")
            .exists()
        )
        result = await self.db.execute(
            select(func.count(), func.count().filter(Task.status == "done")).select_from(Task).where(
                Task.user_id == user_id,
                Task.status != "cancelled",
                ~has_steps,
                Task.created_at >= start,
                Task.created_at < end,
            )
        )
        total, done = result.one()
        return total, done

    # ── Steps (TIME-320) ──────────────────────────────────────────────────────
    # Bulk reads only: Today and Now annotate whole lists, so a per-task query would multiply.

    async def get_many(
        self, task_ids: Iterable[uuid.UUID], user_id: uuid.UUID | None = None
    ) -> list[Task]:
        ids = list(set(task_ids))
        if not ids:
            return []
        q = select(Task).where(Task.id.in_(ids))
        if user_id is not None:
            q = q.where(Task.user_id == user_id)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def step_counts(
        self, parent_ids: Iterable[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[int, int]]:
        """(steps that still count, steps still open) per parent, in one query. A cancelled step counts
        for neither: once deleted it is no longer part of the group."""
        ids = list(set(parent_ids))
        if not ids:
            return {}
        result = await self.db.execute(
            select(
                Task.parent_task_id,
                func.count(Task.id).filter(Task.status != "cancelled"),
                func.count(Task.id).filter(Task.status.in_(("pending", "in_progress"))),
            )
            .where(Task.parent_task_id.in_(ids))
            .group_by(Task.parent_task_id)
        )
        return {parent_id: (total, open_) for parent_id, total, open_ in result.all()}

    async def steps_for(self, parent_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, list[Task]]:
        """Each parent's steps in position order, in one query."""
        ids = list(set(parent_ids))
        if not ids:
            return {}
        result = await self.db.execute(
            select(Task)
            .where(Task.parent_task_id.in_(ids))
            .order_by(Task.parent_task_id, Task.position.nulls_last(), Task.created_at)
        )
        steps: dict[uuid.UUID, list[Task]] = {}
        for step in result.scalars().all():
            steps.setdefault(step.parent_task_id, []).append(step)
        return steps

    async def next_position(self, parent_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.max(Task.position)).where(Task.parent_task_id == parent_id)
        )
        current = result.scalar_one()
        return 0 if current is None else current + 1

    async def parent_links(self, user_id: uuid.UUID) -> dict[uuid.UUID, uuid.UUID]:
        """step id → parent id for every step the user has, so loop checks can follow the waits a step
        inherits from its parent (TIME-322)."""
        result = await self.db.execute(
            select(Task.id, Task.parent_task_id).where(
                Task.user_id == user_id, Task.parent_task_id.is_not(None)
            )
        )
        return {step_id: parent_id for step_id, parent_id in result.all()}

    async def open_tasks_for_matching(
        self, user_id: uuid.UUID, limit: int = 40
    ) -> list[tuple[uuid.UUID, str]]:
        """(id, title) of the user's open tasks that a new capture could be a step of, newest first.

        Only standalone tasks and parents qualify, never steps or calendar events. The list is what
        capture offers the model when it decides whether "add get photos to renew passport" names an
        existing task (TIME-325)."""
        result = await self.db.execute(
            select(Task.id, Task.title)
            .where(
                Task.user_id == user_id,
                Task.parent_task_id.is_(None),
                Task.status.in_(OPEN_STATUSES),
                Task.source != "calendar",
            )
            .order_by(Task.created_at.desc())
            .limit(limit)
        )
        return [(task_id, title) for task_id, title in result.all()]
