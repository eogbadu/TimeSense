from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.task_duration_repository import TaskDurationRepository
from app.services.task_library import classify, get_type, is_known_type


class TaskDurationEstimator:
    """How long the assistant thinks a task will take.

    Two layers: the baseline library (what this kind of task typically takes) and what this user's
    own history says about this TYPE of task. The learned value is shrunk toward the baseline in
    proportion to how much evidence there is, so a single answer nudges the estimate rather than
    becoming it.

    Both layers changed in TIME-286. Previously learning was keyed on a coarse category whose
    catch-all bucket swallowed most real titles, and the learned value replaced the seed outright
    from the very first observation — which is how every task came to read 23 minutes.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._repo = TaskDurationRepository(db)

    @staticmethod
    def resolve_type(title: str, task_type: str | None = None) -> str:
        """The type to estimate against: the task's stored classification when it has a valid one,
        otherwise inferred from the title (rows predating classification stay usable)."""
        return task_type if is_known_type(task_type) else classify(title).key

    # How far the LLM's prediction is allowed to stray from the library's number for that type.
    # A model can confidently say "5 minutes" for a dissertation or "10 hours" for buying milk;
    # the library is generic but never absurd, so it makes a good sanity rail (TIME-305).
    PREDICTION_MIN_FACTOR = 0.25
    PREDICTION_MAX_FACTOR = 4.0

    @classmethod
    def bound_prediction(cls, predicted: int | None, baseline: int) -> int | None:
        """Clamp an LLM prediction to a plausible range around the library baseline."""
        if not predicted or predicted <= 0:
            return None
        low = max(1, int(baseline * cls.PREDICTION_MIN_FACTOR))
        high = max(low, int(baseline * cls.PREDICTION_MAX_FACTOR))
        return max(low, min(high, predicted))

    async def estimate(
        self,
        user_id: uuid.UUID,
        title: str,
        task_type: str | None = None,
        predicted_minutes: int | None = None,
    ) -> tuple[int, str]:
        """Return (estimated_minutes, task_type).

        `predicted_minutes` is the LLM's task-specific guess. It is bounded against the library and
        then used as the PRIOR: it improves the starting point without ever outranking what the
        user's own history says (TIME-305). Without it, behaviour is exactly as before.
        """
        resolved = self.resolve_type(title, task_type)
        baseline = get_type(resolved).typical_minutes
        prior = self.bound_prediction(predicted_minutes, baseline)

        learned = await self._repo.get_minutes(user_id, resolved, prior_minutes=prior)
        if learned is not None:
            return learned, resolved
        # No history yet: the LLM's bounded prediction is a better answer than the generic number.
        return (prior or baseline), resolved

    async def should_ask(
        self, user_id: uuid.UUID, title: str, task_type: str | None = None
    ) -> tuple[bool, str]:
        """Whether to prompt 'how long did that take?' — only while this type is still being learned,
        and never for a task we couldn't classify."""
        resolved = self.resolve_type(title, task_type)
        return await self._repo.learning_active(user_id, resolved), resolved

    async def record_actual(
        self,
        user_id: uuid.UUID,
        title: str,
        actual_minutes: int,
        task_type: str | None = None,
        *,
        task_id: uuid.UUID | None = None,
        estimated_minutes: int | None = None,
    ) -> str:
        """Teach the estimator how long a task actually took. Returns the type it was recorded
        against."""
        resolved = self.resolve_type(title, task_type)
        await self._repo.record_actual(
            user_id, resolved, actual_minutes,
            task_id=task_id, estimated_minutes=estimated_minutes,
        )
        return resolved
