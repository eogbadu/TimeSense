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
@pytest.mark.parametrize("tz", ["America/Los_Angeles", "Asia/Tokyo", "Asia/Kolkata", "UTC"])
async def test_today_includes_untimed_tasks_on_the_users_local_date(client, db_session, tz):
    """Regression (originally: a late-evening user saw an empty "your day is open" screen).

    The client sends its own LOCAL date. That used to disagree with the server's UTC date, and was
    patched over with a "within ±1 day of UTC-today" fudge. Since TIME-283 the server resolves the
    day in the user's stored timezone, so the two agree by construction and untimed pending tasks
    show up — in every zone, not just those near UTC.
    """
    from app.core.localtime import local_today
    from app.services.user_service import UserService
    from app.models.task import Task

    user, _ = await UserService(db_session).get_or_create_user(MOCK_USER.uid, MOCK_USER.email)
    db_session.add(Task(user_id=user.id, title="Go to Walmart", status="pending", priority=3))
    await db_session.flush()

    with _mock_verify(MOCK_USER):
        await client.patch("/api/v1/users/me/profile", headers=_auth_headers(),
                           json={"timezone": tz})
        # Exactly what the device sends: the date it currently is where the user is.
        r = await client.get(f"/api/v1/timeline/today?date={local_today(tz).isoformat()}",
                             headers=_auth_headers())
    assert r.status_code == 200
    assert "Go to Walmart" in [t["title"] for t in r.json()]


@pytest.mark.anyio
async def test_untimed_tasks_do_not_leak_into_other_days(client, db_session):
    """The flip side of dropping the ±1-day fudge: untimed to-dos belong to *today*, so browsing
    another date must not silently show them (the old fudge did, for any date within a day)."""
    from datetime import timedelta
    from app.core.localtime import local_today
    from app.services.user_service import UserService
    from app.models.task import Task

    user, _ = await UserService(db_session).get_or_create_user(MOCK_USER.uid, MOCK_USER.email)
    db_session.add(Task(user_id=user.id, title="Go to Walmart", status="pending", priority=3))
    await db_session.flush()

    with _mock_verify(MOCK_USER):
        await client.patch("/api/v1/users/me/profile", headers=_auth_headers(),
                           json={"timezone": "UTC"})
        other_day = (local_today("UTC") + timedelta(days=3)).isoformat()
        r = await client.get(f"/api/v1/timeline/today?date={other_day}",
                             headers=_auth_headers())
    assert r.status_code == 200
    assert "Go to Walmart" not in [t["title"] for t in r.json()]


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


# ── TIME-283: the timeline day window follows the user's timezone, wherever they are ──────────


async def _set_timezone(client, tz: str) -> None:
    with _mock_verify(MOCK_USER):
        r = await client.patch(
            "/api/v1/users/me/profile", headers=_auth_headers(), json={"timezone": tz}
        )
    assert r.status_code == 200, r.text
    assert r.json()["timezone"] == tz


@pytest.mark.anyio
@pytest.mark.parametrize(
    "tz,local_hour,utc_instant,expected_utc_date",
    [
        # East of UTC: an early-morning local task is the PREVIOUS date in UTC.
        ("Asia/Tokyo", 7, "2026-08-27T22:00:00Z", "2026-08-27"),
        ("Asia/Shanghai", 7, "2026-08-27T23:00:00Z", "2026-08-27"),
        ("Australia/Sydney", 7, "2026-08-27T21:00:00Z", "2026-08-27"),
        # Half-hour offset — the case a whole-hour assumption gets wrong.
        ("Asia/Kolkata", 4, "2026-08-27T22:30:00Z", "2026-08-27"),
        # West of UTC: a late-evening local task is the NEXT date in UTC.
        ("America/Los_Angeles", 21, "2026-08-29T04:00:00Z", "2026-08-29"),
        ("America/New_York", 21, "2026-08-29T01:00:00Z", "2026-08-29"),
    ],
)
async def test_timeline_today_uses_the_users_local_day(
    client, tz, local_hour, utc_instant, expected_utc_date
):
    """A task at `local_hour` on 2026-08-28 in `tz` must appear when asking for 2026-08-28, even
    though the instant belongs to a different UTC date. This is the Japan bug, generalised: the
    same code path has to work for a user in China, Australia, India or the US.
    """
    await _set_timezone(client, tz)
    # Sanity: the fixture really does straddle the UTC date boundary, or the test proves nothing.
    assert utc_instant.startswith(expected_utc_date)
    assert expected_utc_date != "2026-08-28"

    with _mock_verify(MOCK_USER):
        created = await client.post(
            "/api/v1/tasks",
            headers=_auth_headers(),
            json={"title": f"{tz} task", "scheduled_start": utc_instant, "source": "manual"},
        )
        assert created.status_code in (200, 201), created.text

        r = await client.get(
            "/api/v1/timeline/today", headers=_auth_headers(), params={"date": "2026-08-28"}
        )
    assert r.status_code == 200
    titles = [t["title"] for t in r.json()]
    assert f"{tz} task" in titles, f"{tz}: task at {local_hour}:00 local vanished from its own day"


@pytest.mark.anyio
async def test_timeline_excludes_a_task_from_the_neighbouring_local_day(client):
    """The window must still exclude — a Tokyo task an hour BEFORE local midnight belongs to the
    27th, not the 28th, even though both share a UTC date."""
    await _set_timezone(client, "Asia/Tokyo")
    with _mock_verify(MOCK_USER):
        # 23:00 on the 27th in Tokyo == 14:00 UTC on the 27th.
        await client.post(
            "/api/v1/tasks",
            headers=_auth_headers(),
            json={"title": "previous day", "scheduled_start": "2026-08-27T14:00:00Z",
                  "source": "manual"},
        )
        # 00:30 on the 28th in Tokyo == 15:30 UTC on the 27th — same UTC date, different local day.
        await client.post(
            "/api/v1/tasks",
            headers=_auth_headers(),
            json={"title": "just after local midnight", "scheduled_start": "2026-08-27T15:30:00Z",
                  "source": "manual"},
        )
        r = await client.get(
            "/api/v1/timeline/today", headers=_auth_headers(), params={"date": "2026-08-28"}
        )
    titles = [t["title"] for t in r.json()]
    assert "just after local midnight" in titles
    assert "previous day" not in titles


@pytest.mark.anyio
async def test_changing_timezone_moves_the_day_window(client):
    """The traveller case end to end: the same stored task moves in and out of "today" purely
    because the user's timezone changed — no data is rewritten."""
    # 08:00 UTC on the 28th. In Tokyo that is 17:00 on the 28th; in Los Angeles, 01:00 on the 28th.
    with _mock_verify(MOCK_USER):
        await client.post(
            "/api/v1/tasks",
            headers=_auth_headers(),
            json={"title": "travelling task", "scheduled_start": "2026-08-28T08:00:00Z",
                  "source": "manual"},
        )

    for tz in ("Asia/Tokyo", "America/Los_Angeles", "Africa/Lagos", "UTC"):
        await _set_timezone(client, tz)
        with _mock_verify(MOCK_USER):
            r = await client.get(
                "/api/v1/timeline/today", headers=_auth_headers(), params={"date": "2026-08-28"}
            )
        assert "travelling task" in [t["title"] for t in r.json()], f"missing in {tz}"

    # Now a zone where that instant is NOT the 28th: 08:00 UTC is 21:00 on the 28th in Auckland
    # (+12), so still the 28th — use a task at 20:00 UTC instead, which is the 29th there.
    with _mock_verify(MOCK_USER):
        await client.post(
            "/api/v1/tasks",
            headers=_auth_headers(),
            json={"title": "next day in Auckland", "scheduled_start": "2026-08-28T20:00:00Z",
                  "source": "manual"},
        )
    await _set_timezone(client, "Pacific/Auckland")
    with _mock_verify(MOCK_USER):
        r = await client.get(
            "/api/v1/timeline/today", headers=_auth_headers(), params={"date": "2026-08-29"}
        )
    assert "next day in Auckland" in [t["title"] for t in r.json()]
