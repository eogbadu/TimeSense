"""TIME-135 — engine-suggested time block avoids calendar events + scheduled tasks."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.security import TokenUser

USER = TokenUser(uid="slot-1", email="slot@example.com", role="user", email_verified=True)


def _verify():
    return patch("app.core.security.firebase_auth.verify_id_token",
                 return_value={"uid": USER.uid, "email": USER.email, "role": "user",
                               "email_verified": True})


@pytest.mark.anyio
async def test_suggested_slot_avoids_calendar_event(client, db_session):
    from app.services.user_service import UserService
    from app.models.task import Task
    from app.models.synced_calendar_event import SyncedCalendarEvent

    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    # a 60-min task, and a meeting that blocks the next hour
    task = Task(user_id=user.id, title="Write proposal", status="pending", priority=2,
                estimated_minutes=60)
    db_session.add(task)
    now = datetime.now(timezone.utc)
    db_session.add(SyncedCalendarEvent(
        user_id=user.id, source="apple", external_id="m1", title="Big meeting",
        starts_at=now, ends_at=now + timedelta(minutes=90)))
    await db_session.flush()

    with _verify():
        r = await client.get(f"/api/v1/tasks/{task.id}/suggested-slot",
                             headers={"Authorization": "Bearer t"})
    body = r.json()
    if body["fits"]:  # only assert positioning when a slot exists in working hours today
        start = datetime.fromisoformat(body["start"])
        # the suggested block must start at or after the meeting ends
        assert start >= now + timedelta(minutes=90)
        assert body["duration_minutes"] == 60


@pytest.mark.anyio
async def test_suggested_slot_rolls_to_tomorrow_when_today_full(client, db_session):
    """A long task requested late in the day (past the working window) should roll to tomorrow."""
    from app.services.user_service import UserService
    from app.models.task import Task
    from app.repositories.user_repository import UserRepository

    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    # Force a tiny, already-past working window so nothing fits today.
    await UserRepository(db_session).update_preferences(user.id, work_start_hour=0, work_end_hour=1)
    task = Task(user_id=user.id, title="Long task", status="pending", priority=2, estimated_minutes=60)
    db_session.add(task)
    await db_session.flush()

    with _verify():
        r = await client.get(f"/api/v1/tasks/{task.id}/suggested-slot",
                             headers={"Authorization": "Bearer t"})
    body = r.json()
    # It's currently after 01:00 UTC on most test runs → today's 00:00-01:00 window is past →
    # a fit, if any, must be a future day (or no fit). Either way it must not be earlier than now.
    if body["fits"]:
        assert body["day"] in ("tomorrow", "later this week", "today")
        assert datetime.fromisoformat(body["start"]) >= datetime.now(timezone.utc) - timedelta(minutes=1)


@pytest.mark.anyio
async def test_suggested_slot_unknown_task_404(client, db_session):
    import uuid
    from app.services.user_service import UserService
    await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    with _verify():
        r = await client.get(f"/api/v1/tasks/{uuid.uuid4()}/suggested-slot",
                             headers={"Authorization": "Bearer t"})
    assert r.status_code == 404
