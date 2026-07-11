"""Turn the recommendation impression→outcome log into plain-language "what TimeSense has learned"
statements, for a transparency surface in the app (not premium-gated).

Mirrors the engine's own learning thresholds (build_summary / apply_feedback): an action type is a
learned preference once the user has reacted to it enough times one way."""
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
from app.services.recommendation.time_service import part_of_day

HISTORY_WINDOW = timedelta(days=30)
THRESHOLD = 3          # reactions before we call it a learned preference
MAX_PREFERENCES = 6

# Friendlier phrasings for the common action types; others fall back to a de-underscored form.
_ACTION_LABELS = {
    "deep_work": "focus blocks",
    "protect_focus_block": "focus blocks",
    "quick_task": "quick tasks",
    "batch_small_tasks": "batching small tasks",
    "admin_task": "admin tasks",
    "run_nearby_errand": "nearby errands",
    "take_break": "breaks",
    "walk": "walks",
    "prepare_for_meeting": "meeting prep",
    "plan_day": "planning your day",
    "wind_down": "winding down",
    "review_upcoming_day": "reviewing your day",
}

_PART_OF_DAY_LABELS = {
    "early_morning": "the early morning",
    "morning": "the morning",
    "midday": "midday",
    "afternoon": "the afternoon",
    "evening": "the evening",
    "night": "the evening",
}


def _label(action_type: str) -> str:
    return _ACTION_LABELS.get(action_type, action_type.replace("_", " "))


def _local_hour(dt: datetime, tz: str) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    try:
        return dt.astimezone(ZoneInfo(tz)).hour
    except Exception:
        return dt.hour


class LearnedPreferencesService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def for_user(self, user_id: uuid.UUID, user_timezone: str = "UTC") -> dict:
        now = datetime.now(timezone.utc)
        rows = (
            await self.db.execute(
                select(RecommendationEvent).where(
                    RecommendationEvent.user_id == user_id,
                    RecommendationEvent.outcome.is_not(None),
                    RecommendationEvent.action_type.is_not(None),
                    RecommendationEvent.created_at >= now - HISTORY_WINDOW,
                )
            )
        ).scalars().all()

        accepts: dict[str, int] = {}
        rejects: dict[str, int] = {}
        rejects_by_pod: dict[tuple[str, str], int] = {}
        reactions = 0
        for r in rows:
            at = r.action_type
            if r.outcome in POSITIVE_OUTCOMES:
                accepts[at] = accepts.get(at, 0) + 1
                reactions += 1
            elif r.outcome in NEGATIVE_OUTCOMES:
                rejects[at] = rejects.get(at, 0) + 1
                reactions += 1
                pod = part_of_day(_local_hour(r.created_at, user_timezone))
                rejects_by_pod[(at, pod)] = rejects_by_pod.get((at, pod), 0) + 1

        prefs: list[dict] = []
        avoided_types: set[str] = set()
        for at in sorted(set(accepts) | set(rejects)):
            acc, rej = accepts.get(at, 0), rejects.get(at, 0)
            if acc >= THRESHOLD and acc > rej:
                prefs.append({"kind": "prefers", "label": _label(at),
                              "detail": f"You usually act on {_label(at)}."})
            elif rej >= THRESHOLD and rej > acc:
                avoided_types.add(at)
                prefs.append({"kind": "avoids", "label": _label(at),
                              "detail": f"You often pass on {_label(at)}."})

        for (at, pod), n in sorted(rejects_by_pod.items()):
            # A time-specific pattern is more useful than a blanket "avoids", so keep it even then.
            if n >= THRESHOLD:
                prefs.append({"kind": "avoids_at_time", "label": _label(at), "part_of_day": pod,
                              "detail": f"You tend to skip {_label(at)} in {_PART_OF_DAY_LABELS.get(pod, pod)}."})

        return {"preferences": prefs[:MAX_PREFERENCES], "based_on": reactions}
