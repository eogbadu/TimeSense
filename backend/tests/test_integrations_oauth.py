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
async def test_web_platform_callback_returns_to_web(client, db_session):
    """A flow started with platform=web returns the browser to the web app, not the timesense:// deep link."""
    user = User(firebase_uid="uid-web", email="web@example.com")
    db_session.add(user)
    await db_session.flush()
    state = sign_state(str(user.id), "google", platform="web")

    fake = TokenResult(access_token="acc", refresh_token="ref", expires_at=datetime.now(UTC))
    with patch.object(google_oauth, "exchange_code", AsyncMock(return_value=fake)):
        resp = await client.get(
            f"/api/v1/integrations/google/callback?code=abc&state={state}", follow_redirects=False,
        )
    assert resp.status_code == 302
    loc = resp.headers["location"]
    assert loc.startswith("http") and "timesense://" not in loc
    assert "status=connected" in loc and "provider=google" in loc


@pytest.mark.anyio
async def test_web_platform_failure_returns_to_web(client):
    """A web-initiated flow that errors returns to the web failure page (browser can't open timesense://)."""
    state = sign_state("00000000-0000-0000-0000-000000000000", "google", platform="web")
    resp = await client.get(
        f"/api/v1/integrations/google/callback?error=access_denied&state={state}",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    loc = resp.headers["location"]
    assert loc.startswith("http") and "status=failed" in loc


@pytest.mark.anyio
async def test_authorize_platform_web_signs_web(client):
    from urllib.parse import parse_qs, urlparse

    from app.core.oauth_state import decode_state
    with patch.object(google_oauth.settings, "google_client_id", "cid.apps"), \
         patch.object(google_oauth.settings, "google_client_secret", "secret"):
        resp = await client.get("/api/v1/integrations/google/authorize?platform=web")
    assert resp.status_code == 200
    state = parse_qs(urlparse(resp.json()["authorize_url"]).query)["state"][0]
    assert decode_state(state, "google").platform == "web"


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


# ── Microsoft / Outlook (TIME-180) ────────────────────────────────────────────

def test_microsoft_build_authorize_url_has_required_params():
    from app.integrations import microsoft_oauth
    with patch.object(microsoft_oauth.settings, "microsoft_client_id", "ms-cid"), \
         patch.object(microsoft_oauth.settings, "microsoft_redirect_uri", "https://api.example/ms/cb"):
        url = microsoft_oauth.build_authorize_url("STATE-MS")
    assert url.startswith(microsoft_oauth.AUTHORIZE_ENDPOINT)
    assert "client_id=ms-cid" in url
    assert "state=STATE-MS" in url
    assert "Calendars.ReadWrite" in url
    assert "offline_access" in url


@pytest.mark.anyio
async def test_microsoft_authorize_requires_configuration(client):
    from app.integrations import microsoft_oauth
    with patch.object(microsoft_oauth.settings, "microsoft_client_id", ""), \
         patch.object(microsoft_oauth.settings, "microsoft_client_secret", ""):
        resp = await client.get("/api/v1/integrations/microsoft/authorize")
    assert resp.status_code == 503


@pytest.mark.anyio
async def test_microsoft_authorize_returns_url_when_configured(client):
    from app.integrations import microsoft_oauth
    with patch.object(microsoft_oauth.settings, "microsoft_client_id", "ms-cid"), \
         patch.object(microsoft_oauth.settings, "microsoft_client_secret", "ms-secret"):
        resp = await client.get("/api/v1/integrations/microsoft/authorize")
    assert resp.status_code == 200
    assert resp.json()["authorize_url"].startswith(microsoft_oauth.AUTHORIZE_ENDPOINT)


@pytest.mark.anyio
async def test_microsoft_callback_success_stores_tokens(client, db_session):
    from app.integrations import microsoft_oauth
    from app.integrations.microsoft_oauth import TokenResult

    user = User(firebase_uid="uid-ms-cb", email="mscb@example.com")
    db_session.add(user)
    await db_session.flush()
    state = sign_state(str(user.id), "microsoft")

    fake = TokenResult(access_token="ms-acc", refresh_token="ms-ref", expires_at=datetime.now(UTC))
    with patch.object(microsoft_oauth, "exchange_code", AsyncMock(return_value=fake)):
        resp = await client.get(
            f"/api/v1/integrations/microsoft/callback?code=abc&state={state}",
            follow_redirects=False,
        )
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("timesense://integrations/connected")

    integration = await CalendarService(db_session).get_integration(user.id, "microsoft")
    assert integration is not None
    assert integration.access_token == "ms-acc"


@pytest.mark.anyio
async def test_microsoft_callback_bad_state_redirects_to_failure(client):
    resp = await client.get(
        "/api/v1/integrations/microsoft/callback?code=abc&state=nope",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("timesense://integrations/failed")


# ── Microsoft Graph calendar provider ─────────────────────────────────────────

def test_graph_datetime_parser_trims_fractional_seconds():
    from app.integrations.microsoft_calendar import _parse_graph_dt
    dt = _parse_graph_dt("2026-07-10T09:30:00.0000000")
    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (2026, 7, 10, 9, 30)


@pytest.mark.anyio
async def test_microsoft_provider_list_events_maps_graph_payload():
    from datetime import datetime as _dt

    from app.integrations import microsoft_calendar
    from app.integrations.microsoft_calendar import MicrosoftCalendarProvider

    class _Resp:
        status_code = 200
        is_success = True

        def json(self):
            return {"value": [{
                "id": "evt1",
                "subject": "Standup",
                "start": {"dateTime": "2026-07-10T09:00:00.0000000", "timeZone": "UTC"},
                "end": {"dateTime": "2026-07-10T09:15:00.0000000", "timeZone": "UTC"},
                "location": {"displayName": "Room 4"},
                "bodyPreview": "Daily sync",
            }]}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, *a, **k):
            return _Resp()

    with patch.object(microsoft_calendar.httpx, "AsyncClient", return_value=_Client()):
        events = await MicrosoftCalendarProvider().list_events(
            "tok", _dt(2026, 7, 10), _dt(2026, 7, 11)
        )
    assert len(events) == 1
    assert events[0].title == "Standup"
    assert events[0].location == "Room 4"
    assert events[0].provider == "microsoft"


# ── Slack (TIME-181) ──────────────────────────────────────────────────────────

def test_slack_build_authorize_url_has_required_params():
    from app.integrations import slack_oauth
    with patch.object(slack_oauth.settings, "slack_client_id", "slack-cid"), \
         patch.object(slack_oauth.settings, "slack_redirect_uri", "https://api.example/slack/cb"):
        url = slack_oauth.build_authorize_url("STATE-SL")
    assert url.startswith(slack_oauth.AUTHORIZE_ENDPOINT)
    assert "client_id=slack-cid" in url
    assert "state=STATE-SL" in url
    assert "channels%3Ahistory" in url  # scope, url-encoded


@pytest.mark.anyio
async def test_slack_authorize_requires_configuration(client):
    from app.integrations import slack_oauth
    with patch.object(slack_oauth.settings, "slack_client_id", ""), \
         patch.object(slack_oauth.settings, "slack_client_secret", ""):
        resp = await client.get("/api/v1/integrations/slack/authorize")
    assert resp.status_code == 503


@pytest.mark.anyio
async def test_slack_authorize_returns_url_when_configured(client):
    from app.integrations import slack_oauth
    with patch.object(slack_oauth.settings, "slack_client_id", "slack-cid"), \
         patch.object(slack_oauth.settings, "slack_client_secret", "slack-secret"):
        resp = await client.get("/api/v1/integrations/slack/authorize")
    assert resp.status_code == 200
    assert resp.json()["authorize_url"].startswith(slack_oauth.AUTHORIZE_ENDPOINT)


@pytest.mark.anyio
async def test_slack_callback_success_stores_token(client, db_session):
    from app.integrations import slack_oauth
    from app.integrations.slack_oauth import SlackTokenResult
    from app.repositories.slack_repository import SlackIntegrationRepository

    user = User(firebase_uid="uid-sl-cb", email="slcb@example.com")
    db_session.add(user)
    await db_session.flush()
    state = sign_state(str(user.id), "slack")

    fake = SlackTokenResult(access_token="xoxb-tok", team_id="T123")
    with patch.object(slack_oauth, "exchange_code", AsyncMock(return_value=fake)):
        resp = await client.get(
            f"/api/v1/integrations/slack/callback?code=abc&state={state}",
            follow_redirects=False,
        )
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("timesense://integrations/connected")

    integration = await SlackIntegrationRepository(db_session).get_active(user.id)
    assert integration is not None
    assert integration.access_token == "xoxb-tok"
    assert integration.team_id == "T123"


@pytest.mark.anyio
async def test_slack_callback_bad_state_redirects_to_failure(client):
    resp = await client.get(
        "/api/v1/integrations/slack/callback?code=abc&state=nope",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("timesense://integrations/failed")


@pytest.mark.anyio
async def test_slack_exchange_raises_on_ok_false():
    from app.integrations import slack_oauth
    from app.integrations.slack_oauth import SlackOAuthError

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": False, "error": "invalid_code"}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            return _Resp()

    with patch.object(slack_oauth.httpx, "AsyncClient", return_value=_Client()):
        with pytest.raises(SlackOAuthError):
            await slack_oauth.exchange_code("bad")
