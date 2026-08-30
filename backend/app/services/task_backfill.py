"""
Bringing pre-classification tasks up to date when they are read (TIME-311).

A task captured before TIME-285 has no `task_type`, and carries whatever estimate was computed at
the time — including the values produced by the "everything takes 23 minutes" bug, where learning
was keyed on a coarse category whose catch-all bucket swallowed most real titles and the learned
value replaced the seed outright from the very first observation.

TIME-286 and TIME-305 changed how NEW estimates are derived and never revisited the existing rows.
So the user is still shown a 23-minute estimate on a task that plainly takes hours, on a screen that
has otherwise been fixed. The number is wrong, and it is wrong in the exact way they reported.

Done on READ rather than as a bulk migration, deliberately. A migration rewrites every row in one
irreversible pass on numbers derived from a classifier that is itself still being corrected; doing it
lazily means a row is only touched when someone actually looks at it, and a later library change
reaches the rows that matter first.
"""
from __future__ import annotations

import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.services.task_duration_service import TaskDurationEstimator

# Phrases that mean the user SAID how long this takes. A duration someone stated is an instruction,
# not a default, and must survive re-estimation.
#
# Read from `raw_input` — the original capture text — because there is no column recording where an
# estimate came from, and for rows this old there never was one. The text is the only evidence
# available, and it is good evidence: if the words "45 min" are in what they typed, the 45 on the row
# is theirs. Tasks created from now on carry the distinction properly (TIME-305 separates
# `stated_minutes` from `predicted_minutes` at capture).
_STATED_DURATION = re.compile(
    r"""
      \b\d+\s*(?:-\s*\d+\s*)?(?:min|mins|minute|minutes|hr|hrs|hour|hours)\b
    | \b\d+\s*(?:m|h)\b
    | \bhalf\s+an?\s+hour\b
    | \ban?\s+hour\b
    | \bquarter\s+of\s+an\s+hour\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def stated_a_duration(raw_input: str | None) -> bool:
    """Whether the capture text contains a duration the user actually spelled out."""
    return bool(raw_input and _STATED_DURATION.search(raw_input))


class TaskBackfillService:
    """Fills in `task_type` for legacy rows, and re-derives the estimate that came with them."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._estimator = TaskDurationEstimator(db)

    async def backfill(self, user_id: uuid.UUID, tasks: list[Task]) -> list[Task]:
        """Classify and re-estimate any task still missing a type. Returns the same list.

        Cost is bounded by the number of DISTINCT types in the batch, not the number of tasks: the
        estimator is asked once per type and the answer reused, so reading a hundred legacy tasks
        costs a handful of queries rather than a hundred.
        """
        legacy = [t for t in tasks if t.task_type is None]
        if not legacy:
            return tasks

        by_type: dict[str, list[Task]] = {}
        for task in legacy:
            resolved = TaskDurationEstimator.resolve_type(task.title or "")
            by_type.setdefault(resolved, []).append(task)

        changed = False
        for task_type, group in by_type.items():
            minutes, resolved = await self._estimator.estimate(user_id, group[0].title or "", task_type)
            for task in group:
                task.task_type = resolved
                if self._should_reestimate(task):
                    task.estimated_minutes = minutes
                changed = True

        if changed:
            await self.db.flush()
        return tasks

    @staticmethod
    def _should_reestimate(task: Task) -> bool:
        """Replace an estimate only on POSITIVE evidence that it was derived rather than chosen.

        Classifying a legacy row is pure gain and always happens. Overwriting its NUMBER is not: the
        whole complaint is that the app put wrong durations on tasks, and replacing a duration
        someone chose would be the same failure wearing different clothes.

        So the bar is evidence, not absence of evidence:

        * No estimate at all -> nothing to lose, fill it in.
        * Captured text that states a duration ("45 min") -> theirs, keep it.
        * Captured text that states none -> derived by the old pipeline, replace it. This is where
          the "everything takes 23 minutes" rows live; capture always records `raw_input`.
        * No captured text and an estimate already present -> set directly through the API, most
          likely by the user in the app. No evidence it was derived, so leave it alone.

        The last case is the one that matters. There is no column recording where an estimate came
        from — worth adding, since this reasoning would then be a lookup rather than an inference.
        """
        if task.estimated_minutes is None:
            return True
        if not task.raw_input:
            return False
        return not stated_a_duration(task.raw_input)
