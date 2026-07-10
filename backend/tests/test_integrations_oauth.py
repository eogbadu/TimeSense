"""
Tests for the Google Calendar OAuth handshake (TIME-177).

No real network calls — google_oauth.exchange_code is patched. Covers the signed-state helper, the
authorize URL, and the callback (success + every failure branch).
"""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.core.entitlements import require_premium
from app.core.oauth_state import OAuthStateError, sign_state, verify_state
from app.core.security import TokenUser, get_current_user
from app.integrations import google_oauth
from app.integrations.google_oauth import TokenResult
from app.main import app
from app.models import (  # noqa: F401 — register tables
    AssistantPersonality,
    CalendarIntegration,
    ConsentRecord,
    OnboardingState,
    Subscription,
    User,
    UserPreferences,
    UserProfile,
)
from app.models.base import Base
from app.services.calendar_service import CalendarService

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DB, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_session):
    fake_user = TokenUser(uid="uid-oauth-test", email="oauth@example.com", role="user")

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[require_premium] = lambda: fake_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


# ── Signed state ──────────────────────────────────────────────────────────────

def test_state_roundtrip():
    token = sign_state("user-123", "google")
    assert verify_state(token, "google") == "user-123"


def test_state_rejects_wrong_provider():
    token = sign_state("user-123", "google")
    with pytest.raises(OAuthStateError):
        verify_state(token, "microsoft")


def test_state_rejects_tampered():
    token = sign_state("user-123", "google")
    with pytest.raises(OAuthStateError):
        verify_state(token + "x", "google")


def test_state_rejects_expired():
    token = sign_state("user-123", "google", ttl_seconds=-1)
    with pytest.raises(OAuthStateError):
        verify_state(token, "google")


def test_state_rejects_empty():
    with pytest.raises(OAuthStateError):
        verify_state("", "google")


# ── Authorize URL ─────────────────────────────────────────────────────────────

def test_build_authorize_url_has_required_params():
    with patch.object(google_oauth.settings, "google_client_id", "cid.apps"), \
         patch.object(google_oauth.settings, "google_redirect_uri", "https://api.example/cb"):
        url = google_oauth.build_authorize_url("STATE123")
    assert url.startswith(google_oauth.AUTHORIZE_ENDPOINT)
    assert "client_id=cid.apps" in url
    assert "state=STATE123" in url
    assert "access_type=offline" in url
    assert "calendar.events" in url


@pytest.mark.anyio
async def test_authorize_requires_configuration(client):
    with patch.object(google_oauth.settings, "google_client_id", ""), \
         patch.object(google_oauth.settings, "google_client_secret", ""):
        resp = await client.get("/api/v1/integrations/google/authorize")
    assert resp.status_code == 503


@pytest.mark.anyio
async def test_authorize_returns_url_when_configured(client):
    with patch.object(google_oauth.settings, "google_client_id", "cid.apps"), \
         patch.object(google_oauth.settings, "google_client_secret", "secret"):
        resp = await client.get("/api/v1/integrations/google/authorize")
    assert resp.status_code == 200
    assert resp.json()["authorize_url"].startswith(google_oauth.AUTHORIZE_ENDPOINT)


# ── Callback ──────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_callback_success_stores_tokens(client, db_session):
    user = User(firebase_uid="uid-cb", email="cb@example.com")
    db_session.add(user)
    await db_session.flush()
    state = sign_state(str(user.id), "google")

    fake = TokenResult(access_token="acc", refresh_token="ref", expires_at=datetime.now(UTC))
    with patch.object(google_oauth, "exchange_code", AsyncMock(return_value=fake)):
        resp = await client.get(
            f"/api/v1/integrations/google/callback?code=abc&state={state}",
            follow_redirects=False,
        )
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("timesense://integrations/connected")

    integration = await CalendarService(db_session).get_integration(user.id, "google")
    assert integration is not None
    assert integration.access_token == "acc"
    assert integration.refresh_token == "ref"


@pytest.mark.anyio
async def test_callback_bad_state_redirects_to_failure(client):
    with patch.object(google_oauth, "exchange_code", AsyncMock()) as ex:
        resp = await client.get(
            "/api/v1/integrations/google/callback?code=abc&state=garbage",
            follow_redirects=False,
        )
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("timesense://integrations/failed")
    ex.assert_not_awaited()  # never reached the token exchange


@pytest.mark.anyio
async def test_callback_provider_error_redirects_to_failure(client):
    resp = await client.get(
        "/api/v1/integrations/google/callback?error=access_denied",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("timesense://integrations/failed")
