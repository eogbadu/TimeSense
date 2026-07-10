"""
Tests for Notion integration (TIME-051).

Notion gets its own TaskSourceProvider abstraction (structured task import, no LLM detection).
The Notion API call (list_candidate_tasks) is always mocked — no real Notion. Property-extraction
tests exercise the real _extract_title/_extract_due helpers against representative Notion shapes.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.core.security import TokenUser
from app.integrations.notion_source import _extract_due, _extract_title
from app.integrations.task_source_base import SourceTask
from app.models.subscription import Subscription
from app.services.notion_service import NotionNotConnected, NotionService
from app.services.user_service import UserService

MOCK_USER = TokenUser(uid="uid-notion-1", email="notion@example.com", role="user", email_verified=True)
OTHER_USER = TokenUser(uid="uid-notion-2", email="notion-other@example.com", role="user", email_verified=True)

_PATCH_TARGET = "app.services.notion_service.NotionTaskSource.list_candidate_tasks"


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


def _candidates(*specs) -> list[SourceTask]:
    """specs: (title,) or (title, due_datetime)."""
    out = []
    for i, spec in enumerate(specs):
        title = spec[0]
        due = spec[1] if len(spec) > 1 else None
        out.append(SourceTask(external_id=f"page-{i}", title=title, due=due))
    return out


async def _grant_premium(db_session, user: TokenUser):
    user_row, _ = await UserService(db_session).get_or_create_user(user.uid, user.email)
    db_session.add(Subscription(user_id=user_row.id, status="trialing"))
    await db_session.flush()
    return user_row


# ── Structured extraction (real helpers) ──────────────────────────────────────

def test_extract_title_from_title_property():
    props = {
        "Name": {"type": "title", "title": [{"plain_text": "Ship "}, {"plain_text": "the release"}]},
        "Notes": {"type": "rich_text", "rich_text": [{"plain_text": "ignore me"}]},
    }
    assert _extract_title(props) == "Ship the release"


def test_extract_title_missing_returns_empty():
    assert _extract_title({"Notes": {"type": "rich_text", "rich_text": []}}) == ""


def test_extract_due_from_first_date_property():
    props = {
        "Name": {"type": "title", "title": [{"plain_text": "x"}]},
        "Due": {"type": "date", "date": {"start": "2026-07-10"}},
    }
    due = _extract_due(props)
    assert due is not None
    assert due.year == 2026 and due.month == 7 and due.day == 10


def test_extract_due_none_when_no_date_property():
    assert _extract_due({"Name": {"type": "title", "title": [{"plain_text": "x"}]}}) is None


def test_extract_due_none_when_date_empty():
    props = {"Due": {"type": "date", "date": None}}
    assert _extract_due(props) is None


# ── Scan creates pending items, never Tasks ───────────────────────────────────

@pytest.mark.anyio
async def test_scan_creates_pending_items_not_tasks(db_session):
    user = await _grant_premium(db_session, MOCK_USER)
    svc = NotionService(db_session)
    await svc.connect(user.id, access_token="secret_tok")

    due = datetime(2026, 7, 10, tzinfo=timezone.utc)
    with patch(_PATCH_TARGET, new=AsyncMock(return_value=_candidates(("Write spec", due), ("Review PR",)))):
        scanned, items = await svc.scan_database(user.id, database_id="db-1")

    assert scanned == 2
    assert len(items) == 2
    assert items[0].status == "pending"
    assert items[0].created_task_id is None
    assert any(i.due_at is not None for i in items)

    from app.repositories.task_repository import TaskRepository
    assert await TaskRepository(db_session).list_by_user(user.id, limit=50) == []


@pytest.mark.anyio
async def test_scan_skips_already_seen_page(db_session):
    user = await _grant_premium(db_session, MOCK_USER)
    svc = NotionService(db_session)
    await svc.connect(user.id, access_token="secret_tok")

    with patch(_PATCH_TARGET, new=AsyncMock(return_value=_candidates(("Write spec",)))):
        _, first = await svc.scan_database(user.id, database_id="db-1")
        _, second = await svc.scan_database(user.id, database_id="db-1")

    assert len(first) == 1
    assert len(second) == 0


@pytest.mark.anyio
async def test_scan_without_connection_raises(db_session):
    user = await _grant_premium(db_session, MOCK_USER)
    svc = NotionService(db_session)
    with pytest.raises(NotionNotConnected):
        await svc.scan_database(user.id, database_id="db-1")


# ── Import / dismiss approval gate ────────────────────────────────────────────

@pytest.mark.anyio
async def test_import_creates_task_with_notion_source_and_due(db_session):
    user = await _grant_premium(db_session, MOCK_USER)
    svc = NotionService(db_session)
    await svc.connect(user.id, access_token="secret_tok")
    due = datetime(2026, 7, 10, tzinfo=timezone.utc)
    with patch(_PATCH_TARGET, new=AsyncMock(return_value=_candidates(("Write spec", due)))):
        _, items = await svc.scan_database(user.id, database_id="db-1")
    item = items[0]

    imported = await svc.import_item(user.id, item.id)
    assert imported.status == "imported"
    assert imported.created_task_id is not None

    task = await svc.task_repo.get_by_id(imported.created_task_id, user.id)
    assert task is not None
    assert task.source == "notion"
    assert task.title == "Write spec"
    assert task.due_at is not None


@pytest.mark.anyio
async def test_import_twice_raises(db_session):
    user = await _grant_premium(db_session, MOCK_USER)
    svc = NotionService(db_session)
    await svc.connect(user.id, access_token="secret_tok")
    with patch(_PATCH_TARGET, new=AsyncMock(return_value=_candidates(("Write spec",)))):
        _, items = await svc.scan_database(user.id, database_id="db-1")
    item = items[0]

    await svc.import_item(user.id, item.id)
    with pytest.raises(ValueError, match="already imported"):
        await svc.import_item(user.id, item.id)


@pytest.mark.anyio
async def test_dismiss_creates_no_task(db_session):
    user = await _grant_premium(db_session, MOCK_USER)
    svc = NotionService(db_session)
    await svc.connect(user.id, access_token="secret_tok")
    with patch(_PATCH_TARGET, new=AsyncMock(return_value=_candidates(("Write spec",)))):
        _, items = await svc.scan_database(user.id, database_id="db-1")

    assert await svc.dismiss(user.id, items[0].id) is True
    from app.repositories.task_repository import TaskRepository
    assert await TaskRepository(db_session).list_by_user(user.id, limit=50) == []


# ── API-layer tests (premium gate, isolation) ─────────────────────────────────

@pytest.mark.anyio
async def test_scan_without_premium_returns_403(client, db_session):
    from tests.conftest import expire_intro_trial
    await expire_intro_trial(db_session, MOCK_USER.uid, MOCK_USER.email)
    with _mock_verify(MOCK_USER):
        r = await client.post("/api/v1/notion/scan", headers=_auth_headers(), json={"database_id": "db-1"})
    assert r.status_code == 403


@pytest.mark.anyio
async def test_scan_and_import_via_api(client, db_session):
    await _grant_premium(db_session, MOCK_USER)
    with patch(_PATCH_TARGET, new=AsyncMock(return_value=_candidates(("Write spec",), ("Review PR",)))):
        with _mock_verify(MOCK_USER):
            await client.post("/api/v1/notion/connect", headers=_auth_headers(), json={"access_token": "secret"})
            scan = await client.post("/api/v1/notion/scan", headers=_auth_headers(), json={"database_id": "db-1"})
    assert scan.status_code == 200
    data = scan.json()
    assert data["scanned"] == 2
    assert len(data["items"]) == 2
    item_id = data["items"][0]["id"]

    with _mock_verify(MOCK_USER):
        imp = await client.post(f"/api/v1/notion/items/{item_id}/import", headers=_auth_headers())
    assert imp.status_code == 200
    assert imp.json()["created_task_id"] is not None


@pytest.mark.anyio
async def test_pending_items_are_per_user(client, db_session):
    await _grant_premium(db_session, MOCK_USER)
    with patch(_PATCH_TARGET, new=AsyncMock(return_value=_candidates(("Write spec",)))):
        with _mock_verify(MOCK_USER):
            await client.post("/api/v1/notion/connect", headers=_auth_headers(), json={"access_token": "secret"})
            await client.post("/api/v1/notion/scan", headers=_auth_headers(), json={"database_id": "db-1"})

    with _mock_verify(OTHER_USER):
        r = await client.get("/api/v1/notion/pending", headers=_auth_headers())
    assert r.json() == []


@pytest.mark.anyio
async def test_notion_scan_unauthenticated(client):
    r = await client.post("/api/v1/notion/scan", json={"database_id": "db-1"})
    assert r.status_code == 401
