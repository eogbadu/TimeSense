"""
Tests for Slack integration (TIME-049).

Detection-logic tests run at the service layer (own db_session). API-layer tests (premium gate,
scan/confirm/reject flow, isolation) use the shared client/db_session fixtures from conftest.py.
The Slack provider's network call (list_recent_messages) is always mocked — no real Slack.
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.core.security import TokenUser
from app.integrations.message_source_base import SourceMessage
from app.llm.gateway import LLMGateway, LLMResponse, _NoOpProvider, get_llm_gateway, set_llm_gateway
from app.models.subscription import Subscription
from app.services.slack_service import SlackDetectionService, SlackService
from app.services.user_service import UserService

MOCK_USER = TokenUser(uid="uid-slack-1", email="slack@example.com", role="user", email_verified=True)
OTHER_USER = TokenUser(uid="uid-slack-2", email="slack-other@example.com", role="user", email_verified=True)


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
            payload = {"is_action_item": True, "title": "Send the report", "estimated_minutes": 30, "priority": 2}
        else:
            payload = {"is_action_item": False, "title": "", "estimated_minutes": None, "priority": 3}
        return LLMResponse(content=json.dumps(payload), model="mock", provider="mock")


def _set_detect_gateway():
    set_llm_gateway(LLMGateway(provider=_DetectProvider()))


@pytest.fixture(autouse=True)
def reset_gateway():
    import app.llm.gateway as _gw_mod
    original = _gw_mod._gateway
    _set_detect_gateway()
    yield
    _gw_mod._gateway = original


def _messages(*texts: str) -> list[SourceMessage]:
    return [
        SourceMessage(message_id=f"170000000.{i:06d}", channel="C123", text=t, author="U1")
        for i, t in enumerate(texts)
    ]


async def _grant_premium(db_session, user: TokenUser):
    user_row, _ = await UserService(db_session).get_or_create_user(user.uid, user.email)
    db_session.add(Subscription(user_id=user_row.id, status="trialing"))
    await db_session.flush()
    return user_row


# ── Detection-service unit tests ──────────────────────────────────────────────

@pytest.mark.anyio
async def test_detect_flags_action_item():
    detector = SlackDetectionService(get_llm_gateway())
    result = await detector.detect("Please send the report by Friday")
    assert result.is_action_item is True
    assert result.title == "Send the report"
    assert result.priority == 2
    assert result.estimated_minutes == 30


@pytest.mark.anyio
async def test_detect_ignores_non_action_message():
    detector = SlackDetectionService(get_llm_gateway())
    result = await detector.detect("lol that meeting was wild")
    assert result.is_action_item is False


@pytest.mark.anyio
async def test_detect_falls_back_to_non_action_on_llm_failure():
    # _NoOpProvider.complete() raises 503 — detection must degrade to "not an action item".
    set_llm_gateway(LLMGateway(provider=_NoOpProvider()))
    detector = SlackDetectionService(get_llm_gateway())
    result = await detector.detect("Please do the thing")
    assert result.is_action_item is False


# ── Scan creates pending items, never Tasks ───────────────────────────────────

@pytest.mark.anyio
async def test_scan_creates_pending_items_not_tasks(db_session):
    user = await _grant_premium(db_session, MOCK_USER)
    svc = SlackService(db_session, get_llm_gateway())
    await svc.connect(user.id, access_token="xoxb-tok")

    mock_messages = _messages("Please send the report", "just chatting here")
    with patch(
        "app.services.slack_service.SlackMessageSource.list_recent_messages",
        new=AsyncMock(return_value=mock_messages),
    ):
        scanned, detected = await svc.scan_channel(user.id, channel="C123")

    assert scanned == 2
    assert len(detected) == 1
    assert detected[0].detected_title == "Send the report"
    assert detected[0].status == "pending"
    assert detected[0].created_task_id is None

    # No Tasks created by scanning.
    from app.repositories.task_repository import TaskRepository
    tasks = await TaskRepository(db_session).list_by_user(user.id, limit=50)
    assert tasks == []


@pytest.mark.anyio
async def test_scan_skips_already_seen_message(db_session):
    user = await _grant_premium(db_session, MOCK_USER)
    svc = SlackService(db_session, get_llm_gateway())
    await svc.connect(user.id, access_token="xoxb-tok")

    mock_messages = _messages("Please send the report")
    with patch(
        "app.services.slack_service.SlackMessageSource.list_recent_messages",
        new=AsyncMock(return_value=mock_messages),
    ):
        _, first = await svc.scan_channel(user.id, channel="C123")
        _, second = await svc.scan_channel(user.id, channel="C123")

    assert len(first) == 1
    assert len(second) == 0  # same message ts, no duplicate pending item


@pytest.mark.anyio
async def test_scan_without_connection_raises(db_session):
    user = await _grant_premium(db_session, MOCK_USER)
    svc = SlackService(db_session, get_llm_gateway())
    from app.services.slack_service import SlackNotConnected

    with pytest.raises(SlackNotConnected):
        await svc.scan_channel(user.id, channel="C123")


# ── Confirm/reject approval gate ──────────────────────────────────────────────

@pytest.mark.anyio
async def test_confirm_creates_task_with_slack_source(db_session):
    user = await _grant_premium(db_session, MOCK_USER)
    svc = SlackService(db_session, get_llm_gateway())
    await svc.connect(user.id, access_token="xoxb-tok")
    with patch(
        "app.services.slack_service.SlackMessageSource.list_recent_messages",
        new=AsyncMock(return_value=_messages("Please send the report")),
    ):
        _, detected = await svc.scan_channel(user.id, channel="C123")
    item = detected[0]

    confirmed = await svc.confirm(user.id, item.id)
    assert confirmed.status == "confirmed"
    assert confirmed.created_task_id is not None

    task = await svc.task_repo.get_by_id(confirmed.created_task_id, user.id)
    assert task is not None
    assert task.source == "slack"
    assert task.title == "Send the report"


@pytest.mark.anyio
async def test_confirm_twice_raises(db_session):
    user = await _grant_premium(db_session, MOCK_USER)
    svc = SlackService(db_session, get_llm_gateway())
    await svc.connect(user.id, access_token="xoxb-tok")
    with patch(
        "app.services.slack_service.SlackMessageSource.list_recent_messages",
        new=AsyncMock(return_value=_messages("Please send the report")),
    ):
        _, detected = await svc.scan_channel(user.id, channel="C123")
    item = detected[0]

    await svc.confirm(user.id, item.id)
    with pytest.raises(ValueError, match="already confirmed"):
        await svc.confirm(user.id, item.id)


@pytest.mark.anyio
async def test_reject_creates_no_task(db_session):
    user = await _grant_premium(db_session, MOCK_USER)
    svc = SlackService(db_session, get_llm_gateway())
    await svc.connect(user.id, access_token="xoxb-tok")
    with patch(
        "app.services.slack_service.SlackMessageSource.list_recent_messages",
        new=AsyncMock(return_value=_messages("Please send the report")),
    ):
        _, detected = await svc.scan_channel(user.id, channel="C123")
    item = detected[0]

    assert await svc.reject(user.id, item.id) is True
    from app.repositories.task_repository import TaskRepository
    assert await TaskRepository(db_session).list_by_user(user.id, limit=50) == []


# ── API-layer tests (premium gate, isolation) ─────────────────────────────────

@pytest.mark.anyio
async def test_scan_without_premium_returns_403(client):
    with _mock_verify(MOCK_USER):
        r = await client.post("/api/v1/slack/scan", headers=_auth_headers(), json={"channel": "C123"})
    assert r.status_code == 403


@pytest.mark.anyio
async def test_scan_and_confirm_via_api(client, db_session):
    await _grant_premium(db_session, MOCK_USER)
    with patch(
        "app.services.slack_service.SlackMessageSource.list_recent_messages",
        new=AsyncMock(return_value=_messages("Please send the report", "hello world")),
    ):
        with _mock_verify(MOCK_USER):
            await client.post("/api/v1/slack/connect", headers=_auth_headers(), json={"access_token": "xoxb"})
            scan = await client.post("/api/v1/slack/scan", headers=_auth_headers(), json={"channel": "C123"})
    assert scan.status_code == 200
    data = scan.json()
    assert data["scanned"] == 2
    assert len(data["detected"]) == 1
    item_id = data["detected"][0]["id"]

    with _mock_verify(MOCK_USER):
        confirm = await client.post(f"/api/v1/slack/actions/{item_id}/confirm", headers=_auth_headers())
    assert confirm.status_code == 200
    assert confirm.json()["created_task_id"] is not None


@pytest.mark.anyio
async def test_pending_items_are_per_user(client, db_session):
    await _grant_premium(db_session, MOCK_USER)
    with patch(
        "app.services.slack_service.SlackMessageSource.list_recent_messages",
        new=AsyncMock(return_value=_messages("Please send the report")),
    ):
        with _mock_verify(MOCK_USER):
            await client.post("/api/v1/slack/connect", headers=_auth_headers(), json={"access_token": "xoxb"})
            await client.post("/api/v1/slack/scan", headers=_auth_headers(), json={"channel": "C123"})

    with _mock_verify(OTHER_USER):
        r = await client.get("/api/v1/slack/pending", headers=_auth_headers())
    assert r.json() == []


@pytest.mark.anyio
async def test_confirm_other_users_item_404(client, db_session):
    await _grant_premium(db_session, MOCK_USER)
    with patch(
        "app.services.slack_service.SlackMessageSource.list_recent_messages",
        new=AsyncMock(return_value=_messages("Please send the report")),
    ):
        with _mock_verify(MOCK_USER):
            await client.post("/api/v1/slack/connect", headers=_auth_headers(), json={"access_token": "xoxb"})
            scan = await client.post("/api/v1/slack/scan", headers=_auth_headers(), json={"channel": "C123"})
    item_id = scan.json()["detected"][0]["id"]

    with _mock_verify(OTHER_USER):
        r = await client.post(f"/api/v1/slack/actions/{item_id}/confirm", headers=_auth_headers())
    assert r.status_code == 400  # not found for this user → ValueError → 400


@pytest.mark.anyio
async def test_slack_scan_unauthenticated(client):
    r = await client.post("/api/v1/slack/scan", json={"channel": "C123"})
    assert r.status_code == 401
