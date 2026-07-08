"""TIME-131 — Apple Calendar synced events feed the engine."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.security import TokenUser

USER = TokenUser(uid="cal-1", email="cal@example.com", role="user", email_verified=True)


def _verify():
    return patch("app.core.security.firebase_auth.verify_id_token",
                 return_value={"uid": USER.uid, "email": USER.email, "role": "user",
                               "email_verified": True})


def _iso(dt):
    return dt.isoformat()


@pytest.mark.anyio
async def test_sync_stores_and_lists_events(client, db_session):
    from app.services.user_service import UserService
    from app.repositories.synced_calendar_event_repository import SyncedCalendarEventRepository

    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    now = datetime.now(timezone.utc)
    with _verify():
        r = await client.put("/api/v1/calendar/synced", headers={"Authorization": "Bearer t"}, json={
            "source": "apple",
            "events": [
                {"external_id": "e1", "title": "Standup",
                 "starts_at": _iso(now + timedelta(hours=1)), "ends_at": _iso(now + timedelta(hours=1, minutes=30))},
                {"external_id": "e2", "title": "1:1",
                 "starts_at": _iso(now + timedelta(hours=3)), "ends_at": _iso(now + timedelta(hours=4))},
            ],
        })
        assert r.status_code == 200 and r.json()["synced"] == 2
        got = await client.get("/api/v1/calendar/synced/today", headers={"Authorization": "Bearer t"})
    assert {e["title"] for e in got.json()} == {"Standup", "1:1"}


@pytest.mark.anyio
async def test_sync_replaces_previous(client, db_session):
    from app.services.user_service import UserService
    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    now = datetime.now(timezone.utc)
    with _verify():
        await client.put("/api/v1/calendar/synced", headers={"Authorization": "Bearer t"}, json={
            "source": "apple", "events": [{"external_id": "old", "title": "Old",
             "starts_at": _iso(now + timedelta(hours=1)), "ends_at": _iso(now + timedelta(hours=2))}]})
        await client.put("/api/v1/calendar/synced", headers={"Authorization": "Bearer t"}, json={
            "source": "apple", "events": [{"external_id": "new", "title": "New",
             "starts_at": _iso(now + timedelta(hours=1)), "ends_at": _iso(now + timedelta(hours=2))}]})
        got = await client.get("/api/v1/calendar/synced/today", headers={"Authorization": "Bearer t"})
    assert [e["title"] for e in got.json()] == ["New"]


@pytest.mark.anyio
async def test_imminent_meeting_drives_prepare_recommendation(client, db_session):
    """A meeting starting in ~10 min should make the engine recommend preparing for it."""
    from app.services.user_service import UserService
    from app.models.task import Task

    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    db_session.add(Task(user_id=user.id, title="Write the report", status="pending", priority=2,
                        estimated_minutes=60))
    await db_session.flush()
    now = datetime.now(timezone.utc)

    with _verify():
        await client.put("/api/v1/calendar/synced", headers={"Authorization": "Bearer t"}, json={
            "source": "apple",
            "events": [{"external_id": "m1", "title": "Design review",
                        "starts_at": _iso(now + timedelta(minutes=10)),
                        "ends_at": _iso(now + timedelta(minutes=40))}]})
        r = await client.get("/api/v1/now/recommendation", headers={"Authorization": "Bearer t"})
    body = r.json()
    assert body["domain"] == "calendar"
    assert body["action_type"] in ("prepare_for_meeting", "join_meeting")


@pytest.mark.anyio
async def test_all_day_events_do_not_drive_meeting_candidates(client, db_session):
    """An all-day event isn't a meeting — it shouldn't trigger prep/leave or shrink the free block."""
    from app.services.user_service import UserService
    from app.models.task import Task

    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    db_session.add(Task(user_id=user.id, title="Deep work task", status="pending", priority=1,
                        estimated_minutes=45, due_at=datetime.now(timezone.utc) + timedelta(hours=5)))
    await db_session.flush()
    now = datetime.now(timezone.utc)
    with _verify():
        await client.put("/api/v1/calendar/synced", headers={"Authorization": "Bearer t"}, json={
            "source": "apple",
            "events": [{"external_id": "allday", "title": "Vacation", "all_day": True,
                        "starts_at": _iso(now.replace(hour=0, minute=0)),
                        "ends_at": _iso(now.replace(hour=23, minute=59))}]})
        r = await client.get("/api/v1/now/recommendation", headers={"Authorization": "Bearer t"})
    # no meeting candidate from an all-day event
    assert r.json()["action_type"] not in ("prepare_for_meeting", "join_meeting", "leave_for_event")
