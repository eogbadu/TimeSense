"""TIME-216 — email scan → detect → pending EmailActionItem → confirm/reject.

The Gmail fetch is always mocked (via EmailService.fetch_recent); the LLM detector is a stub that
flags a message as an action item iff it contains 'please'. Mirrors test_slack.py.
"""
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.core.security import TokenUser
from app.integrations.email_source_base import EmailMessage
from app.llm.gateway import LLMGateway, LLMResponse, _NoOpProvider, get_llm_gateway, set_llm_gateway
from app.models.subscription import Subscription
from app.repositories.consent_repository import ConsentRepository
from app.services.email_service import EmailConsentRequired, EmailNotConnected, EmailService
from app.services.user_service import UserService

USER = TokenUser(uid="uid-emscan-1", email="es1@example.com", role="user", email_verified=True)
OTHER = TokenUser(uid="uid-emscan-2", email="es2@example.com", role="user", email_verified=True)


def _auth():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser = USER):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role,
                      "email_verified": user.email_verified},
    )


class _DetectProvider(_NoOpProvider):
    async def complete(self, request):
        text = request.prompt.lower()
        if "please" in text:
            payload = {"is_action_item": True, "title": "Review the contract", "estimated_minutes": 20, "priority": 2}
        else:
            payload = {"is_action_item": False, "title": "", "estimated_minutes": None, "priority": 3}
        return LLMResponse(content=json.dumps(payload), model="mock", provider="mock")


@pytest.fixture(autouse=True)
def _detect_gateway():
    import app.llm.gateway as _gw_mod
    original = _gw_mod._gateway
    set_llm_gateway(LLMGateway(provider=_DetectProvider()))
    yield
    _gw_mod._gateway = original


def _emails(*subjects_snippets) -> list[EmailMessage]:
    return [
        EmailMessage(message_id=f"m{i}", thread_id=f"t{i}", subject=subj, sender="a@b.com", snippet=snip)
        for i, (subj, snip) in enumerate(subjects_snippets)
    ]


async def _connect_and_consent(db_session, user_row):
    svc = EmailService(db_session, get_llm_gateway())
    await svc.connect(user_id=user_row.id, provider="gmail", access_token="AT",
                      refresh_token="RT", token_expires_at=None)
    await ConsentRepository(db_session).record(user_row.id, "email_content", True)
    return svc


# ── Service-layer ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_scan_creates_pending_items_not_tasks(db_session):
    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    svc = await _connect_and_consent(db_session, user)
    emails = _emails(("Contract", "Please review the contract"), ("FYI", "Just so you know"))
    with patch.object(EmailService, "fetch_recent", new=AsyncMock(return_value=emails)):
        scanned, detected = await svc.scan(user.id)
    assert scanned == 2 and len(detected) == 1
    assert detected[0].detected_title == "Review the contract" and detected[0].status == "pending"
    assert detected[0].created_task_id is None   # NOT a task yet


@pytest.mark.anyio
async def test_scan_requires_consent(db_session):
    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    svc = EmailService(db_session, get_llm_gateway())
    await svc.connect(user_id=user.id, provider="gmail", access_token="AT", refresh_token="RT",
                      token_expires_at=None)  # connected but NO email_content consent
    with pytest.raises(EmailConsentRequired):
        await svc.scan(user.id)


@pytest.mark.anyio
async def test_scan_without_connection_raises(db_session):
    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    await ConsentRepository(db_session).record(user.id, "email_content", True)
    with pytest.raises(EmailNotConnected):
        await EmailService(db_session, get_llm_gateway()).scan(user.id)


@pytest.mark.anyio
async def test_scan_dedups_already_seen_email(db_session):
    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    svc = await _connect_and_consent(db_session, user)
    emails = _emails(("Contract", "Please review the contract"))
    with patch.object(EmailService, "fetch_recent", new=AsyncMock(return_value=emails)):
        await svc.scan(user.id)
        _, again = await svc.scan(user.id)   # same email id → no new pending
    assert again == []


@pytest.mark.anyio
async def test_confirm_creates_task_with_email_source(db_session):
    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    svc = await _connect_and_consent(db_session, user)
    emails = _emails(("Contract", "Please review the contract"))
    with patch.object(EmailService, "fetch_recent", new=AsyncMock(return_value=emails)):
        _, detected = await svc.scan(user.id)
    item = await svc.confirm(user.id, detected[0].id)
    assert item.status == "confirmed" and item.created_task_id is not None
    task = await svc.task_repo.get_by_id(item.created_task_id, user.id)
    assert task is not None and task.source == "email" and task.title == "Review the contract"


@pytest.mark.anyio
async def test_confirm_twice_raises(db_session):
    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    svc = await _connect_and_consent(db_session, user)
    with patch.object(EmailService, "fetch_recent",
                      new=AsyncMock(return_value=_emails(("C", "Please do it")))):
        _, detected = await svc.scan(user.id)
    await svc.confirm(user.id, detected[0].id)
    with pytest.raises(ValueError):
        await svc.confirm(user.id, detected[0].id)


@pytest.mark.anyio
async def test_reject_creates_no_task(db_session):
    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    svc = await _connect_and_consent(db_session, user)
    with patch.object(EmailService, "fetch_recent",
                      new=AsyncMock(return_value=_emails(("C", "Please do it")))):
        _, detected = await svc.scan(user.id)
    assert await svc.reject(user.id, detected[0].id) is True
    assert await svc.list_pending(user.id) == []


# ── API-layer ─────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_scan_without_premium_returns_403(client, db_session):
    from tests.conftest import expire_intro_trial
    await expire_intro_trial(db_session, USER.uid, USER.email)
    with _mock_verify():
        r = await client.post("/api/v1/email/scan", headers=_auth(), json={})
    assert r.status_code == 403


@pytest.mark.anyio
async def test_scan_without_consent_returns_403(client, db_session):
    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    await EmailService(db_session).connect(user_id=user.id, provider="gmail", access_token="AT",
                                           refresh_token="RT", token_expires_at=None)
    await db_session.commit()
    with _mock_verify():
        r = await client.post("/api/v1/email/scan", headers=_auth(), json={})
    assert r.status_code == 403


@pytest.mark.anyio
async def test_scan_and_confirm_via_api(client, db_session):
    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    await EmailService(db_session).connect(user_id=user.id, provider="gmail", access_token="AT",
                                           refresh_token="RT", token_expires_at=None)
    await ConsentRepository(db_session).record(user.id, "email_content", True)
    await db_session.commit()
    emails = _emails(("Contract", "Please review the contract"))
    with _mock_verify(), patch.object(EmailService, "fetch_recent", new=AsyncMock(return_value=emails)):
        scan = await client.post("/api/v1/email/scan", headers=_auth(), json={})
        assert scan.status_code == 200
        item_id = scan.json()["detected"][0]["id"]
        confirm = await client.post(f"/api/v1/email/actions/{item_id}/confirm", headers=_auth())
    assert confirm.status_code == 200 and confirm.json()["created_task_id"] is not None
