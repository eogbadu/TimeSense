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
from app.models.recommendation_feedback import RecommendationFeedback
from app.models.recommendation_swap import RecommendationSwap
from app.models.task import Task
from app.repositories.recommendation_event_repository import (
    NEGATIVE_OUTCOMES,
    POSITIVE_OUTCOMES,
)
from app.services.recommendation.feedback.apply_feedback import (
    REASON_MIN_SAMPLES,
    SWAP_MIN_SAMPLES,
    FeedbackSummary,
)
from app.services.recommendation.swap_context import ORIGIN_COMPLETION
from app.services.recommendation.time_service import part_of_day
from app.services.task_library import get_type

# How far back we count accept/reject history, and what counts as "recently" dismissed.
HISTORY_WINDOW = timedelta(days=30)
RECENT_DISMISS_WINDOW = timedelta(hours=6)
# Rejections of the same action type at the same part of day before we learn to avoid it then.
AVOID_AT_TIME_THRESHOLD = 3

# What a swap is worth depending on how it was learned (TIME-316).
#
# An explicit swap is a deliberate statement: the user opened a picker and named a replacement. A
# completion-derived swap is inferred from behaviour — they finished something while another task
# was on screen, which is real evidence but much weaker, and they were never asked. Counting them
# equally would let two Done swipes in one afternoon apply the same -18 score bonus that previously
# took two deliberate multi-tap interactions, and these signals can only TIGHTEN recommendations —
# which the project rule (adjustments may relax, never tighten) does not allow on evidence this
# thin. Half a sample means two silent completions alone are never enough, while a completion
# alongside a deliberate swap still crosses the line.
EXPLICIT_SWAP_WEIGHT = 1.0
COMPLETION_SWAP_WEIGHT = 0.5


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

    swap_signals = await _swap_signals(db, user_id, since, current_pod, user_timezone)
    reason_signals = await _reason_signals(db, user_id, since, current_pod, user_timezone)

    return FeedbackSummary(
        rejects=rejects, accepts=accepts,
        recently_dismissed=recently_dismissed, avoided_now=avoided_now,
        **swap_signals, **reason_signals,
    )


async def _swap_signals(db, user_id, since, current_pod, tz) -> dict:
    """What the user has repeatedly chosen — and swapped away from — at THIS part of day.

    A swap is a paired preference, so it carries more than a rejection does: it names both sides.
    The context snapshot stored with each swap is what makes the pairing usable, since "chose an
    errand over deep work" only means something alongside when it happened (TIME-294/296).
    """
    rows = (await db.execute(
        select(RecommendationSwap).where(
            RecommendationSwap.user_id == user_id,
            RecommendationSwap.created_at >= since,
        )
    )).scalars().all()

    chosen: dict[str, float] = {}
    rejected: dict[str, float] = {}
    for row in rows:
        snapshot = row.context_snapshot or {}
        hour = snapshot.get("local_hour")
        pod = part_of_day(hour) if isinstance(hour, int) else \
            part_of_day(_local_hour(row.created_at, tz))
        if pod != current_pod:
            continue
        # A swap the user stated outright counts for more than one merely inferred from what they
        # finished. Rows written before origin existed are explicit by definition.
        weight = (COMPLETION_SWAP_WEIGHT
                  if snapshot.get("origin") == ORIGIN_COMPLETION
                  else EXPLICIT_SWAP_WEIGHT)
        if (c := snapshot.get("chosen_category")):
            chosen[c] = chosen.get(c, 0.0) + weight
        if (r := snapshot.get("rejected_category")):
            rejected[r] = rejected.get(r, 0.0) + weight

    return {
        "preferred_categories_now": {c for c, n in chosen.items() if n >= SWAP_MIN_SAMPLES},
        # Only count a category as swapped-away-from if it isn't ALSO one they often choose then —
        # otherwise a busy category that appears on both sides penalises itself.
        "swapped_away_categories_now": {
            r for r, n in rejected.items()
            if n >= SWAP_MIN_SAMPLES and n > chosen.get(r, 0)
        },
    }


async def _reason_signals(db, user_id, since, current_pod, tz) -> dict:
    """Give each disagree reason a distinct effect.

    Before TIME-296 the reason was read in exactly ONE place — to choose between a 3-hour and a
    24-hour demote window — so "wrong time" and "not a priority" were indistinguishable to scoring
    despite meaning completely different things.
    """
    rows = (await db.execute(
        select(RecommendationFeedback, Task)
        .join(Task, Task.id == RecommendationFeedback.task_id)
        .where(
            RecommendationFeedback.user_id == user_id,
            RecommendationFeedback.signal == "disagree",
            RecommendationFeedback.reason.is_not(None),
            RecommendationFeedback.created_at >= since,
        )
    )).all()

    wrong_time: dict[str, int] = {}
    too_big: dict[str, int] = {}
    not_priority: dict[str, int] = {}
    for feedback, task in rows:
        category = get_type(task.task_type).category if task.task_type else None
        if not category:
            continue
        if feedback.reason == "wrong_time":
            # Only counts against the part of day it was said in — that is the whole claim.
            if part_of_day(_local_hour(feedback.created_at, tz)) == current_pod:
                wrong_time[category] = wrong_time.get(category, 0) + 1
        elif feedback.reason == "too_big":
            too_big[category] = too_big.get(category, 0) + 1
        elif feedback.reason == "not_priority":
            not_priority[category] = not_priority.get(category, 0) + 1

    return {
        "wrong_time_categories_now": {c for c, n in wrong_time.items() if n >= REASON_MIN_SAMPLES},
        "too_big_categories": {c for c, n in too_big.items() if n >= REASON_MIN_SAMPLES},
        "not_priority_categories": {c for c, n in not_priority.items() if n >= REASON_MIN_SAMPLES},
    }
