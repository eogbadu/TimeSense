"""TIME-214 — Gmail read-only OAuth connect + EmailIntegration storage.

The Gmail token exchange is always mocked — no real Google. API-layer tests use the shared
client/db_session fixtures; the premium gate is exercised via the intro-trial helper.
"""
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.core.oauth_state import sign_state
from app.core.security import TokenUser
from app.integrations import gmail_oauth
from app.repositories.email_repository import EmailIntegrationRepository
from app.services.email_service import EmailService
from app.services.user_service import UserService

USER = TokenUser(uid="uid-email-1", email="email1@example.com", role="user", email_verified=True)


def _auth():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser = USER):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role,
                      "email_verified": user.email_verified},
    )


@pytest.fixture
def _configured(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "gid")
    monkeypatch.setattr(settings, "google_client_secret", "gsecret")
    yield


# ── OAuth module ──────────────────────────────────────────────────────────────

def test_authorize_url_requests_readonly_gmail_scope(_configured):
    url = gmail_oauth.build_authorize_url("state123")
    assert "gmail.readonly" in url
    assert "gmail%2Fcallback" in url        # its own (url-encoded) redirect, not the calendar one
    assert "state=state123" in url
    assert "access_type=offline" in url     # so we get a refresh token


# ── Service layer ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_connect_stores_and_disconnect_deactivates(db_session):
    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    svc = EmailService(db_session)
    integ = await svc.connect(
        user_id=user.id, provider="gmail", access_token="at",
        refresh_token="rt", token_expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    assert integ.provider == "gmail" and integ.is_active

    repo = EmailIntegrationRepository(db_session)
    got = await repo.get_active(user.id)
    assert got is not None and got.access_token == "at" and got.refresh_token == "rt"

    assert await svc.disconnect(user.id) is True
    assert await repo.get_active(user.id) is None


@pytest.mark.anyio
async def test_connect_upsert_keeps_refresh_token_when_omitted(db_session):
    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    svc = EmailService(db_session)
    await svc.connect(user_id=user.id, provider="gmail", access_token="at1",
                      refresh_token="rt1", token_expires_at=None)
    # A refresh grant returns no new refresh_token → keep the stored one.
    await svc.connect(user_id=user.id, provider="gmail", access_token="at2",
                      refresh_token=None, token_expires_at=None)
    got = await EmailIntegrationRepository(db_session).get_active(user.id)
    assert got.access_token == "at2" and got.refresh_token == "rt1"


# ── API layer ─────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_gmail_authorize_returns_consent_url(client, db_session, _configured):
    with _mock_verify():
        r = await client.get("/api/v1/integrations/gmail/authorize", headers=_auth())
    assert r.status_code == 200
    assert "gmail.readonly" in r.json()["authorize_url"]


@pytest.mark.anyio
async def test_gmail_authorize_503_when_unconfigured(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "")
    with _mock_verify():
        r = await client.get("/api/v1/integrations/gmail/authorize", headers=_auth())
    assert r.status_code == 503


@pytest.mark.anyio
async def test_gmail_authorize_without_premium_returns_403(client, db_session, _configured):
    from tests.conftest import expire_intro_trial
    await expire_intro_trial(db_session, USER.uid, USER.email)
    with _mock_verify():
        r = await client.get("/api/v1/integrations/gmail/authorize", headers=_auth())
    assert r.status_code == 403


@pytest.mark.anyio
async def test_gmail_callback_exchanges_and_stores(client, db_session):
    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    await db_session.commit()
    state = sign_state(str(user.id), "gmail")
    fake = gmail_oauth.TokenResult(access_token="AT", refresh_token="RT",
                                   expires_at=datetime.now(UTC) + timedelta(hours=1))
    with patch("app.integrations.gmail_oauth.exchange_code", return_value=fake):
        r = await client.get(f"/api/v1/integrations/gmail/callback?code=abc&state={state}",
                             follow_redirects=False)
    assert r.status_code == 302
    got = await EmailIntegrationRepository(db_session).get_active(user.id)
    assert got is not None and got.access_token == "AT" and got.refresh_token == "RT"


@pytest.mark.anyio
async def test_gmail_callback_bad_state_redirects_to_failure(client, db_session):
    with patch("app.integrations.gmail_oauth.exchange_code"):
        r = await client.get("/api/v1/integrations/gmail/callback?code=abc&state=bogus",
                             follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == settings.oauth_failure_redirect
