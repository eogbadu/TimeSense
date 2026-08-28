from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation_swap import RecommendationSwap

# How long the user's own choice stands as the recommendation. Long enough that the app doesn't
# immediately argue back, short enough that a stale choice can't own the rest of the day.
PIN_DURATION = timedelta(hours=3)

# How far back the learning pass looks (TIME-296).
SWAP_HISTORY_WINDOW = timedelta(days=30)


class RecommendationSwapRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        rejected_task_id: uuid.UUID | None,
        chosen_task_id: uuid.UUID | None,
        reason: str | None = None,
        context_snapshot: dict | None = None,
        now: datetime | None = None,
    ) -> RecommendationSwap:
        now = now or datetime.now(timezone.utc)
        row = RecommendationSwap(
            user_id=user_id,
            rejected_task_id=rejected_task_id,
            chosen_task_id=chosen_task_id,
            reason=reason,
            context_snapshot=context_snapshot,
            pinned_until=now + PIN_DURATION,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def active_pin(
        self, user_id: uuid.UUID, now: datetime | None = None
    ) -> RecommendationSwap | None:
        """The most recent swap whose pin hasn't expired, if any."""
        now = now or datetime.now(timezone.utc)
        result = await self.db.execute(
            select(RecommendationSwap)
            .where(
                RecommendationSwap.user_id == user_id,
                RecommendationSwap.chosen_task_id.is_not(None),
                RecommendationSwap.pinned_until > now,
            )
            .order_by(RecommendationSwap.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def release_pin(self, user_id: uuid.UUID, task_id: uuid.UUID) -> None:
        """Drop the pin once the user has acted on it — completing or dismissing the task means the
        choice has been honoured and shouldn't keep overriding the engine."""
        rows = (await self.db.execute(
            select(RecommendationSwap).where(
                RecommendationSwap.user_id == user_id,
                RecommendationSwap.chosen_task_id == task_id,
                RecommendationSwap.pinned_until.is_not(None),
            )
        )).scalars().all()
        for row in rows:
            row.pinned_until = None
        await self.db.flush()

    async def list_recent(
        self, user_id: uuid.UUID, now: datetime | None = None,
        window: timedelta = SWAP_HISTORY_WINDOW,
    ) -> list[RecommendationSwap]:
        """Swap history — the training pairs for TIME-296."""
        now = now or datetime.now(timezone.utc)
        result = await self.db.execute(
            select(RecommendationSwap)
            .where(
                RecommendationSwap.user_id == user_id,
                RecommendationSwap.created_at >= now - window,
            )
            .order_by(RecommendationSwap.created_at.desc())
        )
        return list(result.scalars().all())
