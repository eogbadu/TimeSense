from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task_duration import TaskDurationEstimate
from app.models.task_duration_observation import TaskDurationObservation
from app.services.task_library import GENERAL_KEY, get_type

# Weight given to a new observation when updating the learned mean (exponential moving average).
_LEARN_ALPHA = 0.3

# How many real observations before a type's estimate is "confident" and we stop asking.
LEARNING_SAMPLE_TARGET = 5

# Strength of the library baseline in the blend, expressed as a number of pseudo-observations.
# With k = 3, one observation moves the answer only a quarter of the way from the baseline; it takes
# several consistent observations to fully own the estimate.
#
# This is the second half of the "everything takes 23 minutes" fix. The first half was granularity
# (learning per type instead of per catch-all category). The second is confidence: the old code
# replaced the estimate outright with an EWMA seeded from the FIRST observation, so a single tap on
# a coarse "~15 min" button became the estimate, and the next two "~30 min" taps blended to exactly
# 23 — which then answered for every unclassified task.
BASELINE_WEIGHT = 3


class TaskDurationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_minutes(
        self, user_id: uuid.UUID, task_type: str, prior_minutes: int | None = None
    ) -> int | None:
        """The blended estimate for a type, or None when we have nothing to add to the prior.

        `prior_minutes` lets a caller supply a better starting point than the library's generic
        number — in practice the LLM's task-specific prediction (TIME-305). It replaces the
        BASELINE in the blend rather than overriding anything, so the user's own observed history
        still takes over as evidence accumulates and a bad prediction self-corrects.

        Never answers for the catch-all: a task we couldn't classify must not contribute its
        duration to a bucket that then answers for every other unclassified task.
        """
        if task_type == GENERAL_KEY:
            return None
        row = await self._get(user_id, task_type)
        if row is None or row.sample_count <= 0:
            return None
        baseline = prior_minutes or get_type(task_type).typical_minutes
        return self._blend(row.estimated_minutes, row.sample_count, baseline)

    @staticmethod
    def _blend(learned_minutes: int, sample_count: int, baseline_minutes: int) -> int:
        """Shrink the learned mean toward the library baseline in proportion to how little evidence
        we have: (n * learned + k * baseline) / (n + k).

        How far the estimate travels from the baseline toward what we've actually observed:

            n = 1   25%      n = 10   77%
            n = 3   50%      n = 20   87%
            n = 5   62%      n = 40   93%

        Convergence is asymptotic by design — the baseline never stops contributing entirely, it
        just becomes negligible. That is the point: a handful of coarse taps should nudge the
        estimate, and only sustained evidence should own it.
        """
        n = max(0, sample_count)
        total = n + BASELINE_WEIGHT
        return max(1, round((n * learned_minutes + BASELINE_WEIGHT * baseline_minutes) / total))

    async def learning_active(self, user_id: uuid.UUID, task_type: str) -> bool:
        """True while we still want real-duration feedback for this type — used to only prompt
        'how long did that take?' before the estimate is confident."""
        if task_type == GENERAL_KEY:
            return False        # never ask about something we couldn't classify
        row = await self._get(user_id, task_type)
        return row is None or row.sample_count < LEARNING_SAMPLE_TARGET

    async def _get(self, user_id: uuid.UUID, task_type: str) -> TaskDurationEstimate | None:
        result = await self.db.execute(
            select(TaskDurationEstimate).where(
                TaskDurationEstimate.user_id == user_id,
                TaskDurationEstimate.task_type == task_type,
            )
        )
        return result.scalar_one_or_none()

    async def record_actual(
        self,
        user_id: uuid.UUID,
        task_type: str,
        actual_minutes: int,
        *,
        task_id: uuid.UUID | None = None,
        estimated_minutes: int | None = None,
    ) -> TaskDurationEstimate | None:
        """Fold a real observed duration into the learned mean for this type, and keep the raw
        observation.

        Returns None for the catch-all type: an unclassified task teaches us nothing transferable,
        and letting it accumulate is exactly how one number came to answer for everything.
        """
        actual_minutes = max(1, int(actual_minutes))

        if task_type == GENERAL_KEY:
            return None

        self.db.add(
            TaskDurationObservation(
                user_id=user_id,
                task_id=task_id,
                task_type=task_type,
                estimated_minutes=estimated_minutes,
                actual_minutes=actual_minutes,
                observed_at=datetime.now(timezone.utc),
            )
        )

        row = await self._get(user_id, task_type)
        if row is None:
            row = TaskDurationEstimate(
                user_id=user_id,
                category=get_type(task_type).category,
                task_type=task_type,
                estimated_minutes=actual_minutes,
                sample_count=1,
            )
            self.db.add(row)
        else:
            blended = row.estimated_minutes * (1 - _LEARN_ALPHA) + actual_minutes * _LEARN_ALPHA
            row.estimated_minutes = max(1, round(blended))
            row.sample_count += 1
        await self.db.flush()
        return row

    async def observations_for_type(
        self, user_id: uuid.UUID, task_type: str, limit: int = 100
    ) -> list[TaskDurationObservation]:
        """Raw observations, newest first — the audit trail behind an estimate, and the input to
        estimate-accuracy reporting (TIME-292)."""
        result = await self.db.execute(
            select(TaskDurationObservation)
            .where(
                TaskDurationObservation.user_id == user_id,
                TaskDurationObservation.task_type == task_type,
            )
            .order_by(TaskDurationObservation.observed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
