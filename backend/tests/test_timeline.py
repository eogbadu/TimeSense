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
