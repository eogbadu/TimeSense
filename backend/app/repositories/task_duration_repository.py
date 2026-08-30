from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent import ConsentRecord
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


# Minimum observations before a task type appears in the cross-user calibration report. Doubles as
# a k-anonymity floor: a bucket built from one or two people's data should not be reportable.
CALIBRATION_MIN_SAMPLES = 5


class DurationCalibrationRepository:
    """Cross-user REPORTING on how well the hand-written baselines match reality.

    Reporting, not learning. `learning_and_adaptation_spec.md` states as an invariant that nothing
    one user does affects another, and that the baseline library is the only shared prior and is
    hand-written. This class exists so a human can SEE where those hand-written numbers are wrong
    and correct them deliberately, with the evidence recorded. Nothing here feeds back into any
    user's estimates automatically — doing so would make the invariant false (TIME-303).

    Two constraints shape it:

    * **Consent.** Every other cross-user aggregate in this codebase reads analytics-consent-gated
      sources — `recommendation_events` is gated at write time. `task_duration_observations` is
      written unconditionally, so this filters to consenting users explicitly rather than inheriting
      a gate it doesn't have.
    * **k-anonymity.** A bucket below CALIBRATION_MIN_SAMPLES is suppressed entirely.

    The catch-all is structurally absent: `record_actual` never writes an observation for it.
    """

    ANALYTICS_CONSENT = "analytics"

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _consenting_user_ids(self) -> set[uuid.UUID]:
        """Users whose LATEST analytics decision is 'granted'. Consent is append-only and
        latest-wins, so an earlier grant that was later withdrawn must not count."""
        rows = (await self.db.execute(
            select(ConsentRecord)
            .where(ConsentRecord.consent_type == self.ANALYTICS_CONSENT)
            .order_by(ConsentRecord.created_at.asc())
        )).scalars().all()
        latest: dict[uuid.UUID, bool] = {}
        for row in rows:
            latest[row.user_id] = row.granted
        return {uid for uid, granted in latest.items() if granted}

    async def calibration_by_type(
        self, min_samples: int = CALIBRATION_MIN_SAMPLES
    ) -> list[dict]:
        """Per task type: how long we said, how long it actually took, and the ratio.

        ratio > 1 means we systematically UNDER-estimate that kind of task.
        Aggregated in Python rather than SQL — this is a report, not a hot path, and it keeps the
        query portable across Postgres and the SQLite used in tests (mirrors acceptance_stats).
        """
        consenting = await self._consenting_user_ids()
        if not consenting:
            return []

        rows = (await self.db.execute(
            select(TaskDurationObservation).where(
                TaskDurationObservation.user_id.in_(consenting),
                TaskDurationObservation.estimated_minutes.is_not(None),
            )
        )).scalars().all()

        grouped: dict[str, list[TaskDurationObservation]] = {}
        for row in rows:
            grouped.setdefault(row.task_type, []).append(row)

        out: list[dict] = []
        for task_type, observations in grouped.items():
            if len(observations) < min_samples:
                continue
            actual = [o.actual_minutes for o in observations]
            shown = [o.estimated_minutes for o in observations]
            mean_actual = sum(actual) / len(actual)
            mean_shown = sum(shown) / len(shown)
            baseline = get_type(task_type).typical_minutes
            out.append({
                "task_type": task_type,
                "samples": len(observations),
                "library_baseline": baseline,
                "mean_shown": round(mean_shown, 1),
                "mean_actual": round(mean_actual, 1),
                # Against what the library says, which is the number a human would edit.
                "ratio_vs_baseline": round(mean_actual / baseline, 2) if baseline else None,
                # Against what we actually told the user, which measures the whole pipeline.
                "ratio_vs_shown": round(mean_actual / mean_shown, 2) if mean_shown else None,
                "suggested_baseline": int(round(mean_actual)),
            })
        out.sort(key=lambda r: abs((r["ratio_vs_baseline"] or 1) - 1), reverse=True)
        return out
