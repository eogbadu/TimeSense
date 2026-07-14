"""TIME-222 — synced calendar events become editable tasks (deduped)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.security import TokenUser

USER = TokenUser(uid="calimp-1", email="calimp@example.com", role="user", email_verified=True)


def _verify():
    return patch("app.core.security.firebase_auth.verify_id_token",
                 return_value={"uid": USER.uid, "email": USER.email, "role": "user",
                               "email_verified": True})


def _iso(dt):
    return dt.isoformat()


async def _sync_events(client, events):
    with _verify():
        r = await client.put("/api/v1/calendar/synced", headers={"Authorization": "Bearer t"},
                             json={"source": "apple", "events": events})
    assert r.status_code == 200


@pytest.mark.anyio
async def test_import_creates_editable_tasks_from_events(client, db_session):
    from app.services.user_service import UserService
    from app.repositories.task_repository import TaskRepository

    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    now = datetime.now(timezone.utc)
    await _sync_events(client, [
        {"external_id": "e1", "title": "Design review",
         "starts_at": _iso(now + timedelta(hours=2)), "ends_at": _iso(now + timedelta(hours=3))},
        {"external_id": "e2", "title": "All-day offsite", "all_day": True,
         "starts_at": _iso(now + timedelta(hours=4)), "ends_at": _iso(now + timedelta(hours=8))},
    ])

    with _verify():
        r = await client.post("/api/v1/calendar/import", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200 and r.json()["imported"] == 1   # all-day skipped

    tasks = await TaskRepository(db_session).list_by_user(user.id)
    imported = [t for t in tasks if t.source == "calendar"]
    assert len(imported) == 1
    t = imported[0]
    assert t.title == "Design review" and t.scheduled_start is not None
    assert t.estimated_minutes == 60 and t.calendar_event_id == "apple:e1"


@pytest.mark.anyio
async def test_import_is_deduped(client, db_session):
    from app.services.user_service import UserService
    from app.repositories.task_repository import TaskRepository

    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    now = datetime.now(timezone.utc)
    events = [{"external_id": "e1", "title": "Standup",
               "starts_at": _iso(now + timedelta(hours=1)), "ends_at": _iso(now + timedelta(hours=1, minutes=30))}]
    await _sync_events(client, events)

    with _verify():
        first = await client.post("/api/v1/calendar/import", headers={"Authorization": "Bearer t"})
        await _sync_events(client, events)  # re-sync the same event
        second = await client.post("/api/v1/calendar/import", headers={"Authorization": "Bearer t"})
    assert first.json()["imported"] == 1
    assert second.json()["imported"] == 0   # no duplicate

    tasks = await TaskRepository(db_session).list_by_user(user.id)
    assert len([t for t in tasks if t.source == "calendar"]) == 1
