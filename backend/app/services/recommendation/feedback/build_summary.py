"""Build a FeedbackSummary from the impression→outcome log (TIME-201 telemetry).

This revives the previously-unused apply_feedback seam: it counts how often the user accepted vs
rejected each action type (from recommendation_events.outcome, keyed by the impression's action_type,
which equals the CandidateAction.type the engine ranks on), so the engine can boost/penalize
action types the user consistently likes/dislikes.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation_event import RecommendationEvent
from app.repositories.recommendation_event_repository import (
    NEGATIVE_OUTCOMES,
    POSITIVE_OUTCOMES,
)
from app.services.recommendation.feedback.apply_feedback import FeedbackSummary
from app.services.recommendation.time_service import part_of_day

# How far back we count accept/reject history, and what counts as "recently" dismissed.
HISTORY_WINDOW = timedelta(days=30)
RECENT_DISMISS_WINDOW = timedelta(hours=6)
# Rejections of the same action type at the same part of day before we learn to avoid it then.
AVOID_AT_TIME_THRESHOLD = 3


def _local_hour(dt: datetime, tz: str) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    try:
        return dt.astimezone(ZoneInfo(tz)).hour
    except Exception:
        return dt.hour


async def build_feedback_summary(
    db: AsyncSession, user_id: uuid.UUID, now: datetime | None = None, user_timezone: str = "UTC"
) -> FeedbackSummary:
    now = now or datetime.now(timezone.utc)
    since = now - HISTORY_WINDOW
    current_pod = part_of_day(_local_hour(now, user_timezone))
    rows = (
        await db.execute(
            select(RecommendationEvent).where(
                RecommendationEvent.user_id == user_id,
                RecommendationEvent.outcome.is_not(None),
                RecommendationEvent.action_type.is_not(None),
                RecommendationEvent.created_at >= since,
            )
        )
    ).scalars().all()

    accepts: dict = {}
    rejects: dict = {}
    recently_dismissed: set = set()
    rejects_at_current_pod: dict = {}  # action_type → rejections that happened at the current part of day
    for r in rows:
        at = r.action_type
        if r.outcome in POSITIVE_OUTCOMES:
            accepts[at] = accepts.get(at, 0) + 1
        elif r.outcome in NEGATIVE_OUTCOMES:
            rejects[at] = rejects.get(at, 0) + 1
            oc_at = r.outcome_at
            if oc_at is not None:
                if oc_at.tzinfo is None:
                    oc_at = oc_at.replace(tzinfo=timezone.utc)
                if now - oc_at < RECENT_DISMISS_WINDOW:
                    recently_dismissed.add(at)
            # Time-of-day learning: was this rejection at the same part of day as now?
            if part_of_day(_local_hour(r.created_at, user_timezone)) == current_pod:
                rejects_at_current_pod[at] = rejects_at_current_pod.get(at, 0) + 1

    avoided_now = {at for at, n in rejects_at_current_pod.items() if n >= AVOID_AT_TIME_THRESHOLD}
    return FeedbackSummary(
        rejects=rejects, accepts=accepts,
        recently_dismissed=recently_dismissed, avoided_now=avoided_now,
    )
