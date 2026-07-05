from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.core.security import TokenUser

MOCK_USER = TokenUser(uid="uid-sleep-1", email="sleep@example.com", role="user", email_verified=True)
OTHER_USER = TokenUser(uid="uid-sleep-2", email="sleep-other@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


async def _grant_health_consent(client, user: TokenUser):
    with _mock_verify(user):
        await client.post(
            "/api/v1/consent/",
            headers=_auth_headers(),
            json={"consent_type": "health_data", "granted": True},
        )


def _wake_at(hour: int, minute: int = 0):
    now = datetime.now(timezone.utc)
    return now.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()


@pytest.mark.anyio
async def test_record_event_without_consent_returns_403(client):
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/sleep/events",
            headers=_auth_headers(),
            json={"wake_time": _wake_at(7, 10), "source": "manual"},
        )
    assert r.status_code == 403


@pytest.mark.anyio
async def test_on_time_wake_does_not_suggest_replan(client):
    await _grant_health_consent(client, MOCK_USER)
    # default sleep routine end_minute is 7:00 — 10 minutes late is well under threshold
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/sleep/events",
            headers=_auth_headers(),
            json={"wake_time": _wake_at(7, 10), "source": "healthkit"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["replan_suggested"] is False

    with _mock_verify(MOCK_USER):
        pending = await client.get("/api/v1/notifications/replans/pending", headers=_auth_headers())
    assert pending.json() == []


@pytest.mark.anyio
async def test_late_wake_suggests_replan(client):
    await _grant_health_consent(client, MOCK_USER)
    # default sleep routine end_minute is 7:00 — 75 minutes late clears the 45-minute threshold
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/sleep/events",
            headers=_auth_headers(),
            json={"wake_time": _wake_at(8, 15), "source": "healthkit"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["replan_suggested"] is True

    with _mock_verify(MOCK_USER):
        pending = await client.get("/api/v1/notifications/replans/pending", headers=_auth_headers())
    pending_data = pending.json()
    assert len(pending_data) == 1
    assert pending_data[0]["status"] == "pending"

    with _mock_verify(MOCK_USER):
        notifications = await client.get("/api/v1/notifications", headers=_auth_headers())
    assert any(n["type"] == "replan_request" for n in notifications.json())


@pytest.mark.anyio
async def test_second_late_wake_same_day_does_not_duplicate_replan(client):
    await _grant_health_consent(client, MOCK_USER)
    with _mock_verify(MOCK_USER):
        await client.post(
            "/api/v1/sleep/events",
            headers=_auth_headers(),
            json={"wake_time": _wake_at(8, 15), "source": "healthkit"},
        )
        r = await client.post(
            "/api/v1/sleep/events",
            headers=_auth_headers(),
            json={"wake_time": _wake_at(8, 45), "source": "healthkit"},
        )
    assert r.status_code == 200
    assert r.json()["replan_suggested"] is False

    with _mock_verify(MOCK_USER):
        pending = await client.get("/api/v1/notifications/replans/pending", headers=_auth_headers())
    assert len(pending.json()) == 1


@pytest.mark.anyio
async def test_get_today_returns_latest_event(client):
    await _grant_health_consent(client, MOCK_USER)
    with _mock_verify(MOCK_USER):
        await client.post(
            "/api/v1/sleep/events",
            headers=_auth_headers(),
            json={"wake_time": _wake_at(7, 5), "source": "manual"},
        )
        r = await client.get("/api/v1/sleep/today", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json() is not None


@pytest.mark.anyio
async def test_get_today_returns_null_with_no_events(client):
    await _grant_health_consent(client, MOCK_USER)
    with _mock_verify(MOCK_USER):
        r = await client.get("/api/v1/sleep/today", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json() is None


@pytest.mark.anyio
async def test_sleep_events_are_per_user(client):
    await _grant_health_consent(client, MOCK_USER)
    with _mock_verify(MOCK_USER):
        await client.post(
            "/api/v1/sleep/events",
            headers=_auth_headers(),
            json={"wake_time": _wake_at(8, 15), "source": "healthkit"},
        )

    await _grant_health_consent(client, OTHER_USER)
    with _mock_verify(OTHER_USER):
        r = await client.get("/api/v1/sleep/today", headers=_auth_headers())
    assert r.json() is None

    with _mock_verify(OTHER_USER):
        pending = await client.get("/api/v1/notifications/replans/pending", headers=_auth_headers())
    assert pending.json() == []


@pytest.mark.anyio
async def test_sleep_events_unauthenticated(client):
    r = await client.post(
        "/api/v1/sleep/events", json={"wake_time": _wake_at(7, 10), "source": "manual"}
    )
    assert r.status_code == 401
