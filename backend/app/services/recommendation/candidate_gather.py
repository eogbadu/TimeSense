"""Collect the eligible candidate Tasks + usable-minutes window for the engine. Shared by the /now
endpoints and the proactive-push service so their inputs never drift."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.recommendation_feedback_repository import RecommendationFeedbackRepository
from app.repositories.synced_calendar_event_repository import SyncedCalendarEventRepository
from app.repositories.task_repository import TaskRepository
from app.services.usable_time_service import UsableTimeService


async def gather_candidate_tasks(db: AsyncSession, user, now: datetime):
    """Returns (candidate_tasks, usable_minutes, today_scheduled_tasks). Candidates = pending today +
    overdue + unscheduled, minus tasks suppressed by snooze / 'not now' feedback."""
    repo = TaskRepository(db)
    today = now.date()

    today_tasks = await repo.list_by_user(user_id=user.id, for_date=today, limit=200)
    pending = [t for t in today_tasks if t.status in ("pending", "in_progress")]

    all_pending = await repo.list_by_user(user_id=user.id, status="pending", limit=200)
    already = {p.id for p in pending}

    overdue = [
        t for t in all_pending
        if t.due_at and t.due_at.replace(tzinfo=timezone.utc) < now and t.id not in already
    ]
    already |= {t.id for t in overdue}
    unscheduled = [t for t in all_pending if t.scheduled_start is None and t.id not in already]

    user_tz = user.profile.timezone if user.profile else "UTC"
    # Calendar meetings block usable time too — otherwise free time is overstated (the end-of-day cap
    # clamps to local midnight, so fetching a 24h window is enough; later events are ignored).
    events = await SyncedCalendarEventRepository(db).list_window(user.id, now, now + timedelta(days=1))
    usable_minutes = UsableTimeService().calculate(
        today_tasks, anchor=now, user_timezone=user_tz, events=events
    )

    suppressed = await RecommendationFeedbackRepository(db).get_suppressed_task_ids(user.id, now)
    # Calendar meetings are commitments, not to-dos — never recommend them as the next action. They
    # still block time via today_tasks above; we only drop them from the candidate pool.
    candidates = [
        t for t in (pending + overdue + unscheduled)
        if t.id not in suppressed and t.source != "calendar"
    ]
    return candidates, usable_minutes, today_tasks
