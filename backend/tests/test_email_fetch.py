"""TIME-215 — read-only Gmail fetch (metadata + snippet only), token refresh, email_content consent.

The Gmail HTTP calls are always mocked — no real Google.
"""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.integrations import gmail_oauth
from app.integrations.gmail_source import GmailEmailSource
from app.repositories.consent_repository import VALID_CONSENT_TYPES, ConsentRepository
from app.services.email_service import EmailNotConnected, EmailService
from app.services.user_service import UserService


def _gmail_responses():
    """(list response, per-message metadata responses) mimicking the Gmail REST API."""
    listing = {"messages": [{"id": "m1", "threadId": "t1"}]}
    msg = {
        "id": "m1", "threadId": "t1", "internalDate": "1720000000000",
        "snippet": "Can you review the contract by Tuesday",
        "payload": {"headers": [
            {"name": "Subject", "value": "Contract review"},
            {"name": "From", "value": "Jane <jane@acme.com>"},
        ]},
    }
    return listing, msg


class _Resp:
    def __init__(self, status_code, json_body):
        self.status_code = status_code
        self._json = json_body
        self.is_success = 200 <= status_code < 300

    def json(self):
        return self._json


@pytest.mark.anyio
async def test_gmail_source_returns_metadata_only():
    listing, msg = _gmail_responses()
    calls = []

    async def fake_get(url, headers=None, params=None):
        calls.append((url, params))
        return _Resp(200, listing) if url.endswith("/messages") else _Resp(200, msg)

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=fake_get)):
        emails = await GmailEmailSource().list_recent_emails("AT")

    assert len(emails) == 1
    e = emails[0]
    assert e.subject == "Contract review" and e.sender == "Jane <jane@acme.com>"
    assert e.snippet.startswith("Can you review") and e.message_id == "m1" and e.thread_id == "t1"
    assert e.detection_text == "Contract review\nCan you review the contract by Tuesday"
    # The per-message fetch must use format=metadata (never the body).
    meta_call = [p for (u, p) in calls if not u.endswith("/messages")][0]
    assert ("format", "metadata") in meta_call


@pytest.mark.anyio
async def test_fetch_without_connection_raises(db_session):
    user, _ = await UserService(db_session).get_or_create_user("uid-fetch-0", "f0@example.com")
    with pytest.raises(EmailNotConnected):
        await EmailService(db_session).fetch_recent(user.id)


@pytest.mark.anyio
async def test_expired_token_is_refreshed_before_fetch(db_session):
    user, _ = await UserService(db_session).get_or_create_user("uid-fetch-1", "f1@example.com")
    svc = EmailService(db_session)
    # Connect with an already-expired access token + a refresh token.
    await svc.connect(user_id=user.id, provider="gmail", access_token="OLD",
                      refresh_token="RT", token_expires_at=datetime.now(UTC) - timedelta(minutes=5))

    refreshed = gmail_oauth.TokenResult(access_token="NEW", refresh_token="RT",
                                        expires_at=datetime.now(UTC) + timedelta(hours=1))
    seen_token = {}

    async def fake_list(self, access_token, max_results=25):
        seen_token["t"] = access_token
        return []

    with patch("app.integrations.gmail_oauth.refresh_access_token",
               new=AsyncMock(return_value=refreshed)) as refresh, \
         patch.object(GmailEmailSource, "list_recent_emails", new=fake_list):
        await svc.fetch_recent(user.id)

    refresh.assert_awaited_once()
    assert seen_token["t"] == "NEW"   # the refreshed token was used
    got = await svc.integration_repo.get_active(user.id)
    assert got.access_token == "NEW"  # and persisted


@pytest.mark.anyio
async def test_valid_token_is_not_refreshed(db_session):
    user, _ = await UserService(db_session).get_or_create_user("uid-fetch-2", "f2@example.com")
    svc = EmailService(db_session)
    await svc.connect(user_id=user.id, provider="gmail", access_token="AT",
                      refresh_token="RT", token_expires_at=datetime.now(UTC) + timedelta(hours=1))

    async def fake_list(self, access_token, max_results=25):
        return []

    with patch("app.integrations.gmail_oauth.refresh_access_token", new=AsyncMock()) as refresh, \
         patch.object(GmailEmailSource, "list_recent_emails", new=fake_list):
        await svc.fetch_recent(user.id)
    refresh.assert_not_awaited()


@pytest.mark.anyio
async def test_email_content_is_a_valid_consent_type(db_session):
    assert "email_content" in VALID_CONSENT_TYPES
    user, _ = await UserService(db_session).get_or_create_user("uid-consent-e", "ce@example.com")
    repo = ConsentRepository(db_session)
    await repo.record(user.id, "email_content", True)
    assert (await repo.get_effective(user.id)).get("email_content") is True
