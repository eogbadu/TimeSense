"""What TimeSense learns when a task is finished — especially when it isn't the one it recommended.

The user sometimes gets an opportunity the app couldn't have known about: a better fit for their
mood, or information it simply didn't have. Until TIME-316 that was completely invisible to
learning. `recommendation_events` knew what was recommended and when, `tasks` knew a status changed,
and nothing joined them — so the single most informative thing the user does, choosing differently
and being right, taught nothing.

This is entirely silent. The user completed a task; that is the whole interaction. No extra tap, no
extra question, no "why did you do that instead?" — the product must never become another job to
manage.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.localtime import resolve_zone, user_timezone_of
from app.models.task import Task
from app.models.user import User
from app.repositories.consent_repository import ConsentRepository
from app.repositories.recommendation_event_repository import (
    OUTCOME_SUPERSEDED,
    RecommendationEventRepository,
)
from app.repositories.recommendation_swap_repository import RecommendationSwapRepository
from app.repositories.task_repository import TaskRepository
from app.services.recommendation.swap_context import ORIGIN_COMPLETION, build_swap_context
from app.services.recommendation.time_service import part_of_day

logger = logging.getLogger(__name__)

# How far back "what were we recommending when they did this?" reaches.
#
# Too long and a 9am pick gets paired with a 4pm completion, by which point the context has changed
# and the pairing is noise. Too short and the ordinary case is missed: see the pick, do something
# else for twenty minutes, mark it done. Ninety minutes also comfortably exceeds the ten-minute
# impression dedupe window, so the impression found is still the one that was actually on screen.
LOOKBACK = timedelta(minutes=90)


def _as_utc(dt: datetime) -> datetime:
    """Timestamps read back from the database can be naive, and `.astimezone()` on a naive value
    silently assumes the SERVER's local zone — which would file a completion under the wrong part of
    day. Same guard used throughout the codebase (e.g. `time_service`, `usable_time_service`).
    """
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class TaskCompletionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_completion(
        self, user: User, task: Task, now: datetime | None = None
    ) -> None:
        """Best-effort. A learning failure must never fail the completion itself — the user's task
        is done either way, and losing a signal is infinitely preferable to losing their work."""
        try:
            await self._record(user, task, now or datetime.now(timezone.utc))
        except Exception:  # noqa: BLE001 — deliberately swallowed; see docstring
            logger.exception("completion signal failed for task %s", task.id)

    async def _record(self, user: User, task: Task, now: datetime) -> None:
        swaps = RecommendationSwapRepository(self.db)
        events = RecommendationEventRepository(self.db)
        tz = user_timezone_of(user)

        # 1. A pin means "do this next". Doing it answers the question, so the pin is spent.
        #    Previously only /recommendations/feedback released it, so completing a pinned task from
        #    Now or Today left a stale pin overriding the engine for up to three hours.
        pin = await swaps.active_pin(user.id, now=now)
        had_pin_on_this_task = pin is not None and pin.chosen_task_id == task.id
        if had_pin_on_this_task:
            await swaps.release_pin(user.id, task.id)

        # 2. An impression is consent-gated on analytics, so anything derived from one must be too,
        #    or the gate means nothing. The pin release above is app behaviour, not analytics, and
        #    deliberately happens regardless.
        effective = await ConsentRepository(self.db).get_effective(user.id)
        if not effective.get("analytics"):
            return

        since = now - LOOKBACK
        impression = await events.latest_open_impression(user.id, since=since)
        if impression is None:
            return

        # 3. The user did exactly what was recommended. No "instead of", so no pair to learn.
        #    This finally sets an outcome no client has ever sent: `done` has been in
        #    POSITIVE_OUTCOMES all along while only `agree` could ever reach it.
        if impression.task_id == task.id:
            await events.set_outcome(impression.id, user.id, outcome="done", outcome_at=now)
            return

        # 4. Off-recommendation. Close the recommendation's impression FIRST, so a burst of
        #    completions can't pair every one of them against the same recommendation.
        await events.set_outcome(
            impression.id, user.id, outcome=OUTCOME_SUPERSEDED, outcome_at=now
        )

        # The completed task was shown at some point and the user did it — a genuine accept.
        own = await events.latest_open_impression(user.id, since=since, task_id=task.id)
        if own is not None:
            await events.set_outcome(own.id, user.id, outcome="done", outcome_at=now)

        # Note what is NOT done here: the recommended task is never marked `disagree` or `not_now`.
        # The user didn't reject it — they did something else first and may still do it. Inventing a
        # rejection would suppress a task they still intend to do, which is exactly the overreach
        # the decision log forbids.

        if not self._same_part_of_day(impression.created_at, now, tz):
            # `_swap_signals` buckets by part of day, so a pair straddling the boundary would be
            # filed under a context that never existed.
            return

        if had_pin_on_this_task:
            # They already told us explicitly, and that swap is on record. One preference, one row.
            return

        rejected = await TaskRepository(self.db).get_by_id(impression.task_id, user.id)
        if rejected is None or rejected.id == task.id:
            return
        if await swaps.recent_pair_exists(user.id, rejected.id, task.id, since=since):
            return

        snapshot = await build_swap_context(
            self.db, user, rejected, task, now, tz, origin=ORIGIN_COMPLETION
        )
        # pin=False is load-bearing: the task is already finished, so pinning it would recommend
        # something the user has just completed AND shadow any genuine explicit pin.
        await swaps.create(
            user_id=user.id,
            rejected_task_id=rejected.id,
            chosen_task_id=task.id,
            reason=None,   # they never said why, and a fabricated reason would pollute _reason_signals
            context_snapshot=snapshot,
            now=now,
            pin=False,
        )

    @staticmethod
    def _same_part_of_day(shown_at: datetime, now: datetime, tz: str) -> bool:
        zone = resolve_zone(tz)
        return (part_of_day(_as_utc(shown_at).astimezone(zone).hour)
                == part_of_day(_as_utc(now).astimezone(zone).hour))
