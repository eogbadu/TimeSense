"""TIME-278: Notion/email imports get auto-placed like captures (duration estimate + calendar-aware
slot). Tests the shared autoschedule helper with a fixed `now` so they don't depend on time-of-day."""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.synced_calendar_event import SyncedCalendarEvent
from app.repositories.task_repository import TaskRepository
from app.services.task_autoschedule import autoschedule_task
from app.services.user_service import UserService

# A fixed weekday mid-morning, well inside the default 08–21 working window.
NOW = datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc)  # Wednesday


async def _user(db_session):
    user, _ = await UserService(db_session).get_or_create_user("uid-autosched", "as@example.com")
    return user


@pytest.mark.anyio
async def test_autoschedule_places_untimed_task_and_estimates_duration(db_session):
    user = await _user(db_session)
    task = await TaskRepository(db_session).create(
        user_id=user.id, title="Write Q3 recap", source="notion")
    assert task.estimated_minutes is None

    scheduled = await autoschedule_task(db_session, task, now=NOW)

    assert scheduled is True
    assert task.estimated_minutes is not None and task.estimated_minutes > 0
    assert task.scheduled_start is not None
    assert task.scheduled_end == task.scheduled_start + timedelta(minutes=task.estimated_minutes)
    assert task.auto_scheduled is True
    assert task.scheduled_start >= NOW


@pytest.mark.anyio
async def test_autoschedule_avoids_a_meeting(db_session):
    user = await _user(db_session)
    # A meeting fills 09:00–10:30; a 30-min task must land at/after 10:30.
    db_session.add(SyncedCalendarEvent(
        user_id=user.id, source="apple", external_id="m1", title="Standup",
        starts_at=NOW, ends_at=NOW + timedelta(minutes=90), all_day=False))
    task = await TaskRepository(db_session).create(
        user_id=user.id, title="Email the vendor", source="email", estimated_minutes=30)
    await db_session.flush()

    scheduled = await autoschedule_task(db_session, task, now=NOW)

    assert scheduled is True
    assert task.scheduled_start >= NOW + timedelta(minutes=90)


@pytest.mark.anyio
async def test_autoschedule_leaves_untimed_when_day_is_full(db_session):
    user = await _user(db_session)
    # A meeting covering the entire remaining working window (09:00 → 21:00) leaves no slot.
    db_session.add(SyncedCalendarEvent(
        user_id=user.id, source="apple", external_id="allday-ish", title="Offsite",
        starts_at=NOW, ends_at=NOW.replace(hour=21), all_day=False))
    task = await TaskRepository(db_session).create(
        user_id=user.id, title="Deep work", source="notion", estimated_minutes=60)
    await db_session.flush()

    scheduled = await autoschedule_task(db_session, task, now=NOW)

    assert scheduled is False
    assert task.scheduled_start is None      # gracefully stays untimed


@pytest.mark.anyio
async def test_autoschedule_skips_already_timed_task(db_session):
    user = await _user(db_session)
    start = NOW + timedelta(hours=2)
    task = await TaskRepository(db_session).create(
        user_id=user.id, title="Already planned", source="manual",
        estimated_minutes=30, scheduled_start=start, scheduled_end=start + timedelta(minutes=30))

    scheduled = await autoschedule_task(db_session, task, now=NOW)

    assert scheduled is False
    # Untouched (compare naively — SQLite drops tzinfo on round-trip).
    assert task.scheduled_start.replace(tzinfo=None) == start.replace(tzinfo=None)


@pytest.mark.anyio
async def test_autoschedule_skips_task_due_a_future_day(db_session):
    user = await _user(db_session)
    task = await TaskRepository(db_session).create(
        user_id=user.id, title="Next week thing", source="notion",
        estimated_minutes=30, due_at=NOW + timedelta(days=5))

    scheduled = await autoschedule_task(db_session, task, now=NOW)

    assert scheduled is False                # not due today → not force-placed today
    assert task.scheduled_start is None
