from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation_feedback import RecommendationFeedback

# How long a "not_now" suppresses a task from recommendations before it's eligible
# again — long enough to not nag within the same work session, short enough that a
# still-pending task doesn't vanish for the rest of the day.
NOT_NOW_COOLDOWN = timedelta(hours=4)


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
