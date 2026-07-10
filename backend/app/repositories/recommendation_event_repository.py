from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation_event import RecommendationEvent

# A best-task impression is deduped within this window (Now is polled often; one row per shown pick).
IMPRESSION_DEDUPE_WINDOW = timedelta(minutes=10)

# Outcomes that count as the user accepting vs rejecting the recommendation.
POSITIVE_OUTCOMES = {"agree", "done"}
NEGATIVE_OUTCOMES = {"disagree", "not_now"}


def _summarize(items) -> dict:
    shown = len(items)
    accepted = sum(1 for r in items if r.outcome in POSITIVE_OUTCOMES)
    rejected = sum(1 for r in items if r.outcome in NEGATIVE_OUTCOMES)
    return {
        "shown": shown,
        "accepted": accepted,
        "rejected": rejected,
        "acceptance_rate": round(accepted / shown, 3) if shown else None,
    }


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

    async def acceptance_stats(
        self, start: datetime, end: datetime, user_id: uuid.UUID | None = None
    ) -> dict:
        """Acceptance rate (accepted ÷ shown) overall and per action_type, over [start, end).
        Aggregated in Python (admin metric, not a hot path) so it's DB-agnostic."""
        q = select(RecommendationEvent).where(
            RecommendationEvent.created_at >= start, RecommendationEvent.created_at < end
        )
        if user_id is not None:
            q = q.where(RecommendationEvent.user_id == user_id)
        rows = (await self.db.execute(q)).scalars().all()

        by_action: dict[str, list] = {}
        for r in rows:
            by_action.setdefault(r.action_type or "unknown", []).append(r)
        return {
            "overall": _summarize(rows),
            "by_action_type": [
                {"action_type": k, **_summarize(v)} for k, v in sorted(by_action.items())
            ],
        }

    async def calibration_buckets(
        self, start: datetime, end: datetime, user_id: uuid.UUID | None = None
    ) -> list[dict]:
        """Confidence calibration: for each confidence decile among *reacted* impressions, the mean
        predicted confidence vs the observed acceptance rate (with n, which is noisy when small)."""
        q = select(RecommendationEvent).where(
            RecommendationEvent.created_at >= start,
            RecommendationEvent.created_at < end,
            RecommendationEvent.outcome.is_not(None),
        )
        if user_id is not None:
            q = q.where(RecommendationEvent.user_id == user_id)
        rows = (await self.db.execute(q)).scalars().all()

        buckets: dict[int, list] = {}
        for r in rows:
            b = min(9, max(0, int((r.confidence or 0.0) * 10)))
            buckets.setdefault(b, []).append(r)

        out: list[dict] = []
        for b in range(10):
            items = buckets.get(b)
            if not items:
                continue
            n = len(items)
            predicted = sum(x.confidence for x in items) / n
            accepted = sum(1 for x in items if x.outcome in POSITIVE_OUTCOMES)
            out.append({
                "bucket": round(b / 10, 1),
                "n": n,
                "predicted_mean": round(predicted, 3),
                "observed_accept_rate": round(accepted / n, 3),
            })
        return out
