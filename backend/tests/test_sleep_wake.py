from datetime import datetime, timedelta, timezone
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


@pytest.mark.anyio
async def test_log_sleep_wake(client):
    wake_time = datetime.now(timezone.utc).replace(hour=7, minute=0, second=0, microsecond=0)
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/sleep-wake",
            headers=_auth_headers(),
            json={"wake_time": wake_time.isoformat(), "source": "healthkit"},
        )
    assert r.status_code == 201
    data = r.json()
    assert data["source"] == "healthkit"


@pytest.mark.anyio
async def test_get_today_sleep_wake(client):
    wake_time = datetime.now(timezone.utc).replace(hour=7, minute=0, second=0, microsecond=0)
    with _mock_verify(MOCK_USER):
        await client.post(
            "/api/v1/sleep-wake",
            headers=_auth_headers(),
            json={"wake_time": wake_time.isoformat()},
        )
        r = await client.get("/api/v1/sleep-wake/today", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json() is not None


@pytest.mark.anyio
async def test_no_sleep_wake_today_returns_none(client):
    with _mock_verify(MOCK_USER):
        r = await client.get("/api/v1/sleep-wake/today", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json() is None


@pytest.mark.anyio
async def test_on_time_wake_creates_no_replan(client):
    # Default sleep routine ends (wake) at 07:00 UTC — 07:10 is well within the 45min threshold.
    wake_time = datetime.now(timezone.utc).replace(hour=7, minute=10, second=0, microsecond=0)
    with _mock_verify(MOCK_USER):
        await client.post(
            "/api/v1/sleep-wake",
            headers=_auth_headers(),
            json={"wake_time": wake_time.isoformat()},
        )
        r = await client.get("/api/v1/notifications/replans/pending", headers=_auth_headers())
    assert r.json() == []


@pytest.mark.anyio
async def test_late_wake_creates_pending_replan(client):
    # Default sleep routine ends (wake) at 07:00 UTC — 08:30 is 90 minutes late.
    wake_time = datetime.now(timezone.utc).replace(hour=8, minute=30, second=0, microsecond=0)
    with _mock_verify(MOCK_USER):
        await client.post(
            "/api/v1/sleep-wake",
            headers=_auth_headers(),
            json={"wake_time": wake_time.isoformat()},
        )
        r = await client.get("/api/v1/notifications/replans/pending", headers=_auth_headers())
    assert r.status_code == 200
    replans = r.json()
    assert len(replans) == 1
    assert "later than usual" in replans[0]["reason"]


@pytest.mark.anyio
async def test_late_wake_creates_notification(client):
    wake_time = datetime.now(timezone.utc).replace(hour=8, minute=30, second=0, microsecond=0)
    with _mock_verify(MOCK_USER):
        await client.post(
            "/api/v1/sleep-wake",
            headers=_auth_headers(),
            json={"wake_time": wake_time.isoformat()},
        )
        r = await client.get("/api/v1/notifications", headers=_auth_headers())
    assert any(n["type"] == "replan_request" for n in r.json())


@pytest.mark.anyio
async def test_sleep_wake_events_are_per_user(client):
    wake_time = datetime.now(timezone.utc).replace(hour=7, minute=0, second=0, microsecond=0)
    with _mock_verify(MOCK_USER):
        await client.post(
            "/api/v1/sleep-wake",
            headers=_auth_headers(),
            json={"wake_time": wake_time.isoformat()},
        )
    with _mock_verify(OTHER_USER):
        r = await client.get("/api/v1/sleep-wake/today", headers=_auth_headers())
    assert r.json() is None


@pytest.mark.anyio
async def test_manual_source_accepted(client):
    wake_time = datetime.now(timezone.utc).replace(hour=7, minute=0, second=0, microsecond=0)
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/sleep-wake",
            headers=_auth_headers(),
            json={"wake_time": wake_time.isoformat(), "source": "manual"},
        )
    assert r.json()["source"] == "manual"


@pytest.mark.anyio
async def test_invalid_source_422(client):
    wake_time = datetime.now(timezone.utc).replace(hour=7, minute=0, second=0, microsecond=0)
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/sleep-wake",
            headers=_auth_headers(),
            json={"wake_time": wake_time.isoformat(), "source": "guessed"},
        )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_sleep_wake_unauthenticated(client):
    r = await client.get("/api/v1/sleep-wake/today")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_morning_replan_service_directly(db_session):
    """Direct service test: repeated late wake logging doesn't crash or duplicate unexpectedly."""
    from app.models.user import User
    from app.services.morning_replan import MorningReplanService

    user = User(firebase_uid="uid-sleep-repo", email="sleep-repo@example.com")
    db_session.add(user)
    await db_session.flush()

    wake_time = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
    svc = MorningReplanService(db_session)
    replan = await svc.check_and_propose(user.id, wake_time)
    assert replan is not None
    assert replan.status == "pending"

    on_time = datetime.now(timezone.utc).replace(hour=7, minute=5, second=0, microsecond=0)
    no_replan = await svc.check_and_propose(user.id, on_time)
    assert no_replan is None
