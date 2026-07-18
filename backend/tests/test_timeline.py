from datetime import date, timezone
from unittest.mock import patch

import pytest

from app.core.security import TokenUser

MOCK_USER = TokenUser(uid="uid-tl-1", email="timeline@example.com", role="user", email_verified=True)
OTHER_USER = TokenUser(uid="uid-tl-2", email="other-tl@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={
            "uid": user.uid,
            "email": user.email,
            "role": user.role,
            "email_verified": user.email_verified,
        },
    )


@pytest.mark.anyio
async def test_today_empty(client):
    """No tasks → empty list."""
    with _mock_verify(MOCK_USER):
        r = await client.get("/api/v1/timeline/today", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.anyio
async def test_today_shows_scheduled_tasks(client):
    """Tasks with scheduled_start on today appear in timeline."""
    today = date.today().isoformat()
    with _mock_verify(MOCK_USER):
        await client.post(
            "/api/v1/tasks",
            headers=_auth_headers(),
            json={
                "title": "Morning standup",
                "scheduled_start": f"{today}T09:00:00Z",
                "scheduled_end": f"{today}T09:30:00Z",
                "source": "manual",
            },
        )
        r = await client.get(
            "/api/v1/timeline/today",
            headers=_auth_headers(),
            params={"date": today},
        )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["title"] == "Morning standup"


@pytest.mark.anyio
async def test_today_sorted_by_scheduled_start(client):
    """Timeline items come back sorted ascending by scheduled_start."""
    today = date.today().isoformat()
    with _mock_verify(MOCK_USER):
        for title, hour in [("Lunch", 12), ("Morning run", 7), ("Afternoon review", 15)]:
            await client.post(
                "/api/v1/tasks",
                headers=_auth_headers(),
                json={
                    "title": title,
                    "scheduled_start": f"{today}T{hour:02d}:00:00Z",
                    "source": "manual",
                },
            )
        r = await client.get(
            "/api/v1/timeline/today",
            headers=_auth_headers(),
            params={"date": today},
        )
    assert r.status_code == 200
    titles = [item["title"] for item in r.json()]
    assert titles == ["Morning run", "Lunch", "Afternoon review"]


@pytest.mark.anyio
async def test_today_excludes_other_dates(client):
    """Tasks scheduled on other dates do not appear."""
    today = date.today().isoformat()
    with _mock_verify(MOCK_USER):
        await client.post(
            "/api/v1/tasks",
            headers=_auth_headers(),
            json={
                "title": "Tomorrow task",
                "scheduled_start": "2026-08-01T09:00:00Z",
                "source": "manual",
            },
        )
        r = await client.get(
            "/api/v1/timeline/today",
            headers=_auth_headers(),
            params={"date": today},
        )
    assert r.status_code == 200
    assert all(item["title"] != "Tomorrow task" for item in r.json())


@pytest.mark.anyio
async def test_today_isolation(client):
    """Other users' tasks do not appear."""
    today = date.today().isoformat()
    with _mock_verify(OTHER_USER):
        await client.post(
            "/api/v1/tasks",
            headers=_auth_headers(),
            json={
                "title": "Other user task",
                "scheduled_start": f"{today}T10:00:00Z",
                "source": "manual",
            },
        )
    with _mock_verify(MOCK_USER):
        r = await client.get(
            "/api/v1/timeline/today",
            headers=_auth_headers(),
            params={"date": today},
        )
    assert r.status_code == 200
    assert all(item["title"] != "Other user task" for item in r.json())


@pytest.mark.anyio
async def test_today_unauthenticated(client):
    """Unauthenticated request rejected."""
    r = await client.get("/api/v1/timeline/today")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_today_includes_untimed_pending_tasks(client, db_session):
    """A captured (unscheduled, pending) task shows on Today so the user sees their to-do list."""
    from app.services.user_service import UserService
    from app.models.task import Task

    user, _ = await UserService(db_session).get_or_create_user(MOCK_USER.uid, MOCK_USER.email)
    db_session.add(Task(user_id=user.id, title="Buy milk", status="pending", priority=3))
    await db_session.flush()

    with _mock_verify(MOCK_USER):
        r = await client.get("/api/v1/timeline/today", headers=_auth_headers())
    assert r.status_code == 200
    titles = [t["title"] for t in r.json()]
    assert "Buy milk" in titles


@pytest.mark.anyio
async def test_today_includes_untimed_tasks_across_utc_boundary(client, db_session):
    """Regression: a late-evening user's LOCAL date lags UTC, so the client sends yesterday's date.
    Untimed pending tasks must still show (this caused the empty 'your day is open' screen)."""
    from datetime import datetime, timedelta, timezone
    from app.services.user_service import UserService
    from app.models.task import Task

    user, _ = await UserService(db_session).get_or_create_user(MOCK_USER.uid, MOCK_USER.email)
    db_session.add(Task(user_id=user.id, title="Go to Walmart", status="pending", priority=3))
    await db_session.flush()

    # The client's local date is one day behind the server's UTC date.
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
    with _mock_verify(MOCK_USER):
        r = await client.get(f"/api/v1/timeline/today?date={yesterday}", headers=_auth_headers())
    assert r.status_code == 200
    assert "Go to Walmart" in [t["title"] for t in r.json()]


@pytest.mark.anyio
async def test_today_plan_weaves_events_and_excludes_calendar_tasks(client, db_session):
    """TIME-276: the unified plan interleaves read-only calendar events with tasks, in time order,
    and hides legacy source='calendar' tasks (they show as events instead — no double-listing)."""
    from datetime import datetime, timezone
    from app.models.synced_calendar_event import SyncedCalendarEvent
    from app.models.task import Task
    from app.services.user_service import UserService

    user, _ = await UserService(db_session).get_or_create_user(MOCK_USER.uid, MOCK_USER.email)
    today = datetime.now(timezone.utc).date()

    def _at(h, m):
        return datetime(today.year, today.month, today.day, h, m, tzinfo=timezone.utc)

    db_session.add(Task(user_id=user.id, title="Write report", status="pending", priority=3,
                        scheduled_start=_at(14, 0), scheduled_end=_at(15, 0), source="manual"))
    # Legacy imported meeting-as-task: must NOT appear as a task row.
    db_session.add(Task(user_id=user.id, title="Imported meeting", status="pending", priority=3,
                        scheduled_start=_at(9, 0), scheduled_end=_at(9, 30), source="calendar"))
    db_session.add(SyncedCalendarEvent(
        user_id=user.id, source="apple", external_id="evt1", title="Standup",
        starts_at=_at(10, 0), ends_at=_at(10, 15), all_day=False))
    db_session.add(SyncedCalendarEvent(
        user_id=user.id, source="apple", external_id="allday", title="Holiday",
        starts_at=_at(0, 0), ends_at=_at(23, 59), all_day=True))
    await db_session.flush()

    with _mock_verify(MOCK_USER):
        r = await client.get(f"/api/v1/timeline/today/plan?date={today.isoformat()}",
                             headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    pairs = [(e["kind"], e["title"]) for e in data]
    assert ("event", "Standup") in pairs
    assert ("task", "Write report") in pairs
    assert ("task", "Imported meeting") not in pairs   # excluded — shown as an event elsewhere
    assert ("event", "Holiday") not in pairs           # all-day omitted

    # Time-ordered: the 10:00 meeting comes before the 14:00 task.
    titles = [e["title"] for e in data]
    assert titles.index("Standup") < titles.index("Write report")

    # Event rows are read-only (no task payload); task rows carry the full task.
    event = next(e for e in data if e["kind"] == "event")
    assert event["task"] is None
    task = next(e for e in data if e["kind"] == "task")
    assert task["task"]["title"] == task["title"]
