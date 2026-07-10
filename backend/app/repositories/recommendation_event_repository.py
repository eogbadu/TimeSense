from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation_event import RecommendationEvent

# A best-task impression is deduped within this window (Now is polled often; one row per shown pick).
IMPRESSION_DEDUPE_WINDOW = timedelta(minutes=10)


class RecommendationEventRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_impression(
        self,
        user_id: uuid.UUID,
        task_id: uuid.UUID,
        surface: str,
        confidence: float,
        action_type: str | None = None,
        domain: str | None = None,
        score: float | None = None,
        rank: int = 0,
        explanation: dict | None = None,
    ) -> RecommendationEvent:
        """Log that a recommendation was shown, returning the row (its id is surfaced to clients).
        Deduped on (user, task, surface) with no outcome yet, within the window, to bound writes."""
        since = datetime.now(timezone.utc) - IMPRESSION_DEDUPE_WINDOW
        existing = (
            await self.db.execute(
                select(RecommendationEvent)
                .where(
                    RecommendationEvent.user_id == user_id,
                    RecommendationEvent.task_id == task_id,
                    RecommendationEvent.surface == surface,
                    RecommendationEvent.outcome.is_(None),
                    RecommendationEvent.created_at >= since,
                )
                .order_by(RecommendationEvent.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

        event = RecommendationEvent(
            user_id=user_id, task_id=task_id, surface=surface, confidence=confidence,
            action_type=action_type, domain=domain, score=score, rank=rank,
            explanation=explanation or {},
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def set_outcome(
        self,
        event_id: uuid.UUID,
        user_id: uuid.UUID,
        outcome: str,
        outcome_at: datetime | None = None,
        feedback_id: uuid.UUID | None = None,
    ) -> bool:
        """Record how the user reacted to a shown recommendation. No-op (False) if the event isn't
        found or doesn't belong to the user."""
        event = (
            await self.db.execute(
                select(RecommendationEvent).where(
                    RecommendationEvent.id == event_id,
                    RecommendationEvent.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if event is None:
            return False
        event.outcome = outcome
        event.outcome_at = outcome_at or datetime.now(timezone.utc)
        event.feedback_id = feedback_id
        await self.db.flush()
        return True
