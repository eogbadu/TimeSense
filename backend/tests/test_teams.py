"""
Tests for Microsoft Teams integration (TIME-050). Mirrors test_slack.py.

The Teams provider's Graph network call (list_recent_messages) is always mocked — no real Teams.
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.core.security import TokenUser
from app.integrations.message_source_base import SourceMessage
from app.llm.gateway import LLMGateway, LLMResponse, _NoOpProvider, get_llm_gateway, set_llm_gateway
from app.models.subscription import Subscription
from app.services.action_item_detection import ActionItemDetectionService
from app.services.teams_service import TeamsNotConnected, TeamsService
from app.services.user_service import UserService

MOCK_USER = TokenUser(uid="uid-teams-1", email="teams@example.com", role="user", email_verified=True)
OTHER_USER = TokenUser(uid="uid-teams-2", email="teams-other@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


class _DetectProvider(_NoOpProvider):
    """LLM stub that flags a message as an action item iff it contains the word 'please'."""

    async def complete(self, request):
        import json

        text = request.prompt.lower()
        if "please" in text:
            payload = {"is_action_item": True, "title": "Send the deck", "estimated_minutes": 20, "priority": 2}
        else:
            payload = {"is_action_item": False, "title": "", "estimated_minutes": None, "priority": 3}
        return LLMResponse(content=json.dumps(payload), model="mock", provider="mock")


@pytest.fixture(autouse=True)
def reset_gateway():
    import app.llm.gateway as _gw_mod
    original = _gw_mod._gateway
    set_llm_gateway(LLMGateway(provider=_DetectProvider()))
    yield
    _gw_mod._gateway = original


def _messages(*texts: str) -> list[SourceMessage]:
    return [
        SourceMessage(message_id=f"msg-{i}", channel="19:conv@thread.v2", text=t, author="U1")
        for i, t in enumerate(texts)
    ]


async def _grant_premium(db_session, user: TokenUser):
    user_row, _ = await UserService(db_session).get_or_create_user(user.uid, user.email)
    db_session.add(Subscription(user_id=user_row.id, status="trialing"))
    await db_session.flush()
    return user_row


_PATCH_TARGET = "app.services.teams_service.TeamsMessageSource.list_recent_messages"


# ── Shared detection (reused from Slack) ──────────────────────────────────────

@pytest.mark.anyio
async def test_detect_flags_action_item():
    detector = ActionItemDetectionService(get_llm_gateway())
    result = await detector.detect("Please send the deck")
    assert result.is_action_item is True
    assert result.title == "Send the deck"


@pytest.mark.anyio
async def test_detect_falls_back_on_llm_failure():
    set_llm_gateway(LLMGateway(provider=_NoOpProvider()))
    detector = ActionItemDetectionService(get_llm_gateway())
    result = await detector.detect("Please do the thing")
    assert result.is_action_item is False


# ── Scan creates pending items, never Tasks ───────────────────────────────────

@pytest.mark.anyio
async def test_scan_creates_pending_items_not_tasks(db_session):
    user = await _grant_premium(db_session, MOCK_USER)
    svc = TeamsService(db_session, get_llm_gateway())
    await svc.connect(user.id, access_token="graph-tok")

    with patch(_PATCH_TARGET, new=AsyncMock(return_value=_messages("Please send the deck", "just chatting"))):
        scanned, detected = await svc.scan_conversation(user.id, conversation_id="19:conv@thread.v2")

    assert scanned == 2
    assert len(detected) == 1
    assert detected[0].detected_title == "Send the deck"
    assert detected[0].status == "pending"
    assert detected[0].created_task_id is None

    from app.repositories.task_repository import TaskRepository
    assert await TaskRepository(db_session).list_by_user(user.id, limit=50) == []


@pytest.mark.anyio
async def test_scan_skips_already_seen_message(db_session):
    user = await _grant_premium(db_session, MOCK_USER)
    svc = TeamsService(db_session, get_llm_gateway())
    await svc.connect(user.id, access_token="graph-tok")

    with patch(_PATCH_TARGET, new=AsyncMock(return_value=_messages("Please send the deck"))):
        _, first = await svc.scan_conversation(user.id, conversation_id="19:conv@thread.v2")
        _, second = await svc.scan_conversation(user.id, conversation_id="19:conv@thread.v2")

    assert len(first) == 1
    assert len(second) == 0


@pytest.mark.anyio
async def test_scan_without_connection_raises(db_session):
    user = await _grant_premium(db_session, MOCK_USER)
    svc = TeamsService(db_session, get_llm_gateway())
    with pytest.raises(TeamsNotConnected):
        await svc.scan_conversation(user.id, conversation_id="19:conv@thread.v2")


# ── Confirm/reject approval gate ──────────────────────────────────────────────

@pytest.mark.anyio
async def test_confirm_creates_task_with_teams_source(db_session):
    user = await _grant_premium(db_session, MOCK_USER)
    svc = TeamsService(db_session, get_llm_gateway())
    await svc.connect(user.id, access_token="graph-tok")
    with patch(_PATCH_TARGET, new=AsyncMock(return_value=_messages("Please send the deck"))):
        _, detected = await svc.scan_conversation(user.id, conversation_id="19:conv@thread.v2")
    item = detected[0]

    confirmed = await svc.confirm(user.id, item.id)
    assert confirmed.status == "confirmed"
    assert confirmed.created_task_id is not None

    task = await svc.task_repo.get_by_id(confirmed.created_task_id, user.id)
    assert task is not None
    assert task.source == "teams"
    assert task.title == "Send the deck"


@pytest.mark.anyio
async def test_confirm_twice_raises(db_session):
    user = await _grant_premium(db_session, MOCK_USER)
    svc = TeamsService(db_session, get_llm_gateway())
    await svc.connect(user.id, access_token="graph-tok")
    with patch(_PATCH_TARGET, new=AsyncMock(return_value=_messages("Please send the deck"))):
        _, detected = await svc.scan_conversation(user.id, conversation_id="19:conv@thread.v2")
    item = detected[0]

    await svc.confirm(user.id, item.id)
    with pytest.raises(ValueError, match="already confirmed"):
        await svc.confirm(user.id, item.id)


@pytest.mark.anyio
async def test_reject_creates_no_task(db_session):
    user = await _grant_premium(db_session, MOCK_USER)
    svc = TeamsService(db_session, get_llm_gateway())
    await svc.connect(user.id, access_token="graph-tok")
    with patch(_PATCH_TARGET, new=AsyncMock(return_value=_messages("Please send the deck"))):
        _, detected = await svc.scan_conversation(user.id, conversation_id="19:conv@thread.v2")
    item = detected[0]

    assert await svc.reject(user.id, item.id) is True
    from app.repositories.task_repository import TaskRepository
    assert await TaskRepository(db_session).list_by_user(user.id, limit=50) == []


# ── API-layer tests (premium gate, isolation) ─────────────────────────────────

@pytest.mark.anyio
async def test_scan_without_premium_returns_403(client):
    with _mock_verify(MOCK_USER):
        r = await client.post("/api/v1/teams/scan", headers=_auth_headers(), json={"conversation_id": "19:c"})
    assert r.status_code == 403


@pytest.mark.anyio
async def test_scan_and_confirm_via_api(client, db_session):
    await _grant_premium(db_session, MOCK_USER)
    with patch(_PATCH_TARGET, new=AsyncMock(return_value=_messages("Please send the deck", "hi team"))):
        with _mock_verify(MOCK_USER):
            await client.post("/api/v1/teams/connect", headers=_auth_headers(), json={"access_token": "graph"})
            scan = await client.post("/api/v1/teams/scan", headers=_auth_headers(), json={"conversation_id": "19:c"})
    assert scan.status_code == 200
    data = scan.json()
    assert data["scanned"] == 2
    assert len(data["detected"]) == 1
    item_id = data["detected"][0]["id"]

    with _mock_verify(MOCK_USER):
        confirm = await client.post(f"/api/v1/teams/actions/{item_id}/confirm", headers=_auth_headers())
    assert confirm.status_code == 200
    assert confirm.json()["created_task_id"] is not None


@pytest.mark.anyio
async def test_pending_items_are_per_user(client, db_session):
    await _grant_premium(db_session, MOCK_USER)
    with patch(_PATCH_TARGET, new=AsyncMock(return_value=_messages("Please send the deck"))):
        with _mock_verify(MOCK_USER):
            await client.post("/api/v1/teams/connect", headers=_auth_headers(), json={"access_token": "graph"})
            await client.post("/api/v1/teams/scan", headers=_auth_headers(), json={"conversation_id": "19:c"})

    with _mock_verify(OTHER_USER):
        r = await client.get("/api/v1/teams/pending", headers=_auth_headers())
    assert r.json() == []


@pytest.mark.anyio
async def test_teams_scan_unauthenticated(client):
    r = await client.post("/api/v1/teams/scan", json={"conversation_id": "19:c"})
    assert r.status_code == 401
