"""Tests for error monitoring (Sentry-optional) and the analytics pipeline (TIME-054)."""
from unittest.mock import patch

import pytest

from app.core import monitoring
from app.core.security import TokenUser
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.consent_repository import ConsentRepository
from app.services.analytics_service import AnalyticsService
from app.services.user_service import UserService

USER = TokenUser(uid="uid-analytics-1", email="a1@example.com", role="user", email_verified=True)
ADMIN = TokenUser(uid="uid-analytics-admin", email="admin@example.com", role="admin", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


async def _user_with_analytics(db_session, granted: bool):
    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    await ConsentRepository(db_session).record(user.id, "analytics", granted)
    await db_session.flush()
    return user


# ── Monitoring ────────────────────────────────────────────────────────────────

def test_monitoring_disabled_without_dsn():
    # Default settings have no SENTRY_DSN → monitoring stays disabled and init is a no-op.
    assert monitoring.is_enabled() is False
    monitoring.init_monitoring()
    assert monitoring.is_enabled() is False


def test_capture_exception_is_safe_when_disabled():
    # Must never raise even though monitoring is off.
    monitoring.capture_exception(ValueError("boom"), context={"path": "/x"})


# ── Analytics service (consent-gated) ─────────────────────────────────────────

@pytest.mark.anyio
async def test_track_records_when_consented(db_session):
    user = await _user_with_analytics(db_session, granted=True)
    event = await AnalyticsService(db_session).track("task_captured", user_id=user.id, properties={"source": "capture"})
    assert event is not None
    assert event.event_name == "task_captured"
    counts = await AnalyticsRepository(db_session).counts_by_event()
    assert counts.get("task_captured") == 1


@pytest.mark.anyio
async def test_track_skips_without_consent(db_session):
    user = await _user_with_analytics(db_session, granted=False)
    event = await AnalyticsService(db_session).track("task_captured", user_id=user.id)
    assert event is None
    counts = await AnalyticsRepository(db_session).counts_by_event()
    assert counts == {}


@pytest.mark.anyio
async def test_track_system_event_without_user(db_session):
    # No user_id → no consent check → recorded.
    event = await AnalyticsService(db_session).track("app_started", user_id=None)
    assert event is not None
    assert event.user_id is None


# ── Capture endpoint emits an event ───────────────────────────────────────────

@pytest.mark.anyio
async def test_capture_emits_task_captured_event(client, db_session):
    await _user_with_analytics(db_session, granted=True)
    with _mock_verify(USER):
        r = await client.post("/api/v1/capture", headers=_auth_headers(), json={"raw_input": "buy milk"})
    assert r.status_code == 201
    counts = await AnalyticsRepository(db_session).counts_by_event()
    assert counts.get("task_captured") == 1


@pytest.mark.anyio
async def test_capture_no_event_without_consent(client, db_session):
    await _user_with_analytics(db_session, granted=False)
    with _mock_verify(USER):
        r = await client.post("/api/v1/capture", headers=_auth_headers(), json={"raw_input": "buy milk"})
    assert r.status_code == 201  # capture still works; analytics just skipped
    counts = await AnalyticsRepository(db_session).counts_by_event()
    assert counts.get("task_captured") is None


# ── Admin analytics endpoint ──────────────────────────────────────────────────

@pytest.mark.anyio
async def test_admin_analytics_counts(client, db_session):
    await AnalyticsRepository(db_session).create("task_captured", None, "{}")
    await AnalyticsRepository(db_session).create("task_captured", None, "{}")
    await AnalyticsRepository(db_session).create("app_started", None, "{}")
    await db_session.flush()
    with _mock_verify(ADMIN):
        r = await client.get("/api/v1/admin/analytics", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["event_counts"]["task_captured"] == 2
    assert data["total"] == 3


@pytest.mark.anyio
async def test_admin_analytics_forbidden_for_normal_user(client):
    with _mock_verify(USER):
        r = await client.get("/api/v1/admin/analytics", headers=_auth_headers())
    assert r.status_code == 403
