from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation_feedback import RecommendationFeedback
from app.models.task import Task
from app.models.user import User

# How long a "not_now" suppresses a task from recommendations before it's eligible
# again — long enough to not nag within the same work session, short enough that a
# still-pending task doesn't vanish for the rest of the day.
NOT_NOW_COOLDOWN = timedelta(hours=4)

# How long a "disagree" DEMOTES (never hides) a task — long enough to surface a different
# recommendation right after the user rejects one, short enough that the task reappears
# later the same session once other candidates fade.
DISAGREE_DEMOTE_WINDOW = timedelta(hours=3)

# When the user gives a stronger reason ("not relevant" / "too big"), keep the task down longer —
# a lightweight form of learning from the reason (TIME-271).
LONG_DEMOTE_WINDOW = timedelta(hours=24)
LONG_DEMOTE_REASONS = frozenset({"not_relevant", "too_big"})


class RecommendationFeedbackRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_suppressed_task_ids(
        self, user_id: uuid.UUID, now: datetime | None = None
    ) -> set[uuid.UUID]:
        """Task IDs to exclude from recommendations based on each task's most recent feedback.

        A task is suppressed if its latest feedback is an active snooze (snooze_until
        still in the future) or a not_now within the cooldown window. Older feedback that
        has since been superseded (e.g. a later snooze, or an expired not_now) does not
        suppress — only the latest signal per task matters.
        """
        now = now or datetime.now(timezone.utc)
        result = await self.db.execute(
            select(RecommendationFeedback)
            .where(RecommendationFeedback.user_id == user_id)
            .order_by(RecommendationFeedback.created_at.desc())
        )

        latest_by_task: dict[uuid.UUID, RecommendationFeedback] = {}
        for fb in result.scalars().all():
            latest_by_task.setdefault(fb.task_id, fb)

        suppressed: set[uuid.UUID] = set()
        for task_id, fb in latest_by_task.items():
            if fb.signal == "snooze" and fb.snooze_until is not None:
                snooze_until = fb.snooze_until
                if snooze_until.tzinfo is None:
                    snooze_until = snooze_until.replace(tzinfo=timezone.utc)
                if snooze_until > now:
                    suppressed.add(task_id)
            elif fb.signal == "not_now":
                created_at = fb.created_at
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                if now - created_at < NOT_NOW_COOLDOWN:
                    suppressed.add(task_id)

        return suppressed

    async def get_recently_disagreed_task_ids(
        self, user_id: uuid.UUID, now: datetime | None = None
    ) -> set[uuid.UUID]:
        """Task IDs to DEMOTE (not hide) because the user recently 'disagreed' with recommending
        them. Uses the latest feedback per task, so a later agree/done/snooze clears the demotion;
        only a `disagree` within DISAGREE_DEMOTE_WINDOW counts.
        """
        now = now or datetime.now(timezone.utc)
        result = await self.db.execute(
            select(RecommendationFeedback)
            .where(RecommendationFeedback.user_id == user_id)
            .order_by(RecommendationFeedback.created_at.desc())
        )

        latest_by_task: dict[uuid.UUID, RecommendationFeedback] = {}
        for fb in result.scalars().all():
            latest_by_task.setdefault(fb.task_id, fb)

        demoted: set[uuid.UUID] = set()
        for task_id, fb in latest_by_task.items():
            if fb.signal != "disagree":
                continue
            created_at = fb.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            window = LONG_DEMOTE_WINDOW if fb.reason in LONG_DEMOTE_REASONS else DISAGREE_DEMOTE_WINDOW
            if now - created_at < window:
                demoted.add(task_id)
        return demoted

    async def count_signals_in_range(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> dict[str, int]:
        """Count of each feedback signal recorded in [start, end)."""
        result = await self.db.execute(
            select(RecommendationFeedback.signal, func.count())
            .where(
                RecommendationFeedback.user_id == user_id,
                RecommendationFeedback.created_at >= start,
                RecommendationFeedback.created_at < end,
            )
            .group_by(RecommendationFeedback.signal)
        )
        return {signal: count for signal, count in result.all()}

    async def list_recent_across_users(
        self, limit: int = 50
    ) -> list[tuple[RecommendationFeedback, str, str]]:
        """Admin-only: most recent feedback across every user, joined with the user's email
        and the task's title for display. Returns (feedback, user_email, task_title) tuples."""
        result = await self.db.execute(
            select(RecommendationFeedback, User.email, Task.title)
            .join(User, User.id == RecommendationFeedback.user_id)
            .join(Task, Task.id == RecommendationFeedback.task_id)
            .order_by(RecommendationFeedback.created_at.desc())
            .limit(limit)
        )
        return [(fb, email, title) for fb, email, title in result.all()]
