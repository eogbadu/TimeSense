"""TIME-326: sub-items and "Blocked by" from a Notion database survive import.

The Notion API is always mocked. Links are made whenever both sides of a relation have been imported,
in either order, and a link TimeSense can't represent is skipped without failing the import.
"""
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.core.security import TokenUser
from app.integrations.notion_source import _extract_relations
from app.integrations.task_source_base import SourceTask
from app.llm.base import LLMResponse
from app.llm.gateway import LLMGateway, set_llm_gateway
from app.models.task import Task
from app.repositories.notion_repository import NotionImportItemRepository
from app.repositories.task_prerequisite_repository import TaskPrerequisiteRepository
from app.repositories.task_repository import TaskRepository
from app.services.notion_service import NotionService
from app.services.user_service import UserService

USER = TokenUser(uid="uid-notion-rel", email="notion-rel@example.com", role="user", email_verified=True)
HEADERS = {"Authorization": "Bearer test-token"}
_PATCH_TARGET = "app.services.notion_service.NotionTaskSource.list_candidate_tasks"


def _signed_in():
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": USER.uid, "email": USER.email, "role": "user", "email_verified": True},
    )


async def _connected_user(db_session):
    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    await NotionService(db_session).connect(user.id, "notion-token")
    return user


async def _scan(db_session, user, *pages: SourceTask):
    with patch(_PATCH_TARGET, new=AsyncMock(return_value=list(pages))):
        await NotionService(db_session).scan_database(user.id, "db-1")


async def _import(db_session, user, page_id: str):
    item = (await NotionImportItemRepository(db_session).by_pages(user.id, [page_id]))[page_id]
    return await NotionService(db_session).import_item(user.id, item.id)


async def _task_for(db_session, user, page_id: str) -> Task:
    item = (await NotionImportItemRepository(db_session).by_pages(user.id, [page_id]))[page_id]
    task = await TaskRepository(db_session).get_by_id(item.created_task_id, user.id)
    await db_session.refresh(task)
    return task


def _page(page_id, title, parent=None, blocked_by=()):
    return SourceTask(external_id=page_id, title=title, parent_external_id=parent,
                      prerequisite_external_ids=list(blocked_by))


# ── Reading relations ─────────────────────────────────────────────────────────

def test_sub_item_and_blocked_by_relations_are_read():
    props = {
        "Name": {"type": "title", "title": [{"plain_text": "Mail it"}]},
        "Parent item": {"type": "relation", "relation": [{"id": "page-passport"}]},
        "Blocked by": {"type": "relation", "relation": [{"id": "page-form"}, {"id": "page-stamps"}]},
        "Sub-item": {"type": "relation", "relation": []},
    }
    assert _extract_relations(props) == ("page-passport", ["page-form", "page-stamps"])


def test_only_relation_properties_count():
    props = {
        "Parent": {"type": "rich_text", "rich_text": [{"plain_text": "not a relation"}]},
        "Depends on": {"type": "relation", "relation": [{"id": "page-a"}]},
    }
    assert _extract_relations(props) == (None, ["page-a"])


def test_a_database_without_relations_has_none():
    assert _extract_relations({"Name": {"type": "title", "title": []}}) == (None, [])


@pytest.mark.anyio
async def test_a_scan_keeps_the_relations_on_the_pending_item(db_session):
    user = await _connected_user(db_session)
    await _scan(db_session, user, _page("page-mail", "Mail it", parent="page-passport",
                                        blocked_by=["page-form"]))

    item = (await NotionImportItemRepository(db_session).by_pages(user.id, ["page-mail"]))["page-mail"]

    assert (item.external_parent_id, item.external_prereq_ids) == ("page-passport", ["page-form"])


# ── Sub-items ─────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_a_sub_item_imported_after_its_parent_becomes_its_step(db_session):
    user = await _connected_user(db_session)
    await _scan(db_session, user, _page("page-passport", "Renew passport"),
                _page("page-photos", "Get photos", parent="page-passport"))

    await _import(db_session, user, "page-passport")
    await _import(db_session, user, "page-photos")

    passport = await _task_for(db_session, user, "page-passport")
    photos = await _task_for(db_session, user, "page-photos")
    assert photos.parent_task_id == passport.id


@pytest.mark.anyio
async def test_a_parent_imported_after_its_sub_item_collects_it(db_session):
    user = await _connected_user(db_session)
    await _scan(db_session, user, _page("page-passport", "Renew passport"),
                _page("page-photos", "Get photos", parent="page-passport"))

    await _import(db_session, user, "page-photos")
    await _import(db_session, user, "page-passport")

    passport = await _task_for(db_session, user, "page-passport")
    photos = await _task_for(db_session, user, "page-photos")
    assert photos.parent_task_id == passport.id


@pytest.mark.anyio
async def test_a_sub_item_of_a_sub_item_is_imported_without_the_link(db_session):
    user = await _connected_user(db_session)
    await _scan(db_session, user, _page("page-passport", "Renew passport"),
                _page("page-photos", "Get photos", parent="page-passport"),
                _page("page-booth", "Find a photo booth", parent="page-photos"))

    for page_id in ("page-passport", "page-photos", "page-booth"):
        item = await _import(db_session, user, page_id)
        assert item.status == "imported"

    booth = await _task_for(db_session, user, "page-booth")
    assert booth.parent_task_id is None


# ── Blocked by ────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_blocked_by_becomes_a_wait_in_either_import_order(db_session):
    user = await _connected_user(db_session)
    await _scan(db_session, user,
                _page("page-invoice", "Get invoice"),
                _page("page-pay", "Pay contractor", blocked_by=["page-invoice"]),
                _page("page-quote", "Get quote"),
                _page("page-sign", "Sign contract", blocked_by=["page-quote"]))

    await _import(db_session, user, "page-invoice")
    await _import(db_session, user, "page-pay")
    await _import(db_session, user, "page-sign")
    await _import(db_session, user, "page-quote")

    edges = await TaskPrerequisiteRepository(db_session).edges_for_user(user.id)
    pay, invoice = await _task_for(db_session, user, "page-pay"), await _task_for(db_session, user, "page-invoice")
    sign, quote = await _task_for(db_session, user, "page-sign"), await _task_for(db_session, user, "page-quote")
    assert set(edges) == {(pay.id, invoice.id), (sign.id, quote.id)}


@pytest.mark.anyio
async def test_a_notion_loop_does_not_fail_the_import(db_session):
    user = await _connected_user(db_session)
    await _scan(db_session, user, _page("page-a", "A", blocked_by=["page-b"]),
                _page("page-b", "B", blocked_by=["page-a"]))

    await _import(db_session, user, "page-a")
    item = await _import(db_session, user, "page-b")

    assert item.status == "imported"
    assert len(await TaskPrerequisiteRepository(db_session).edges_for_user(user.id)) == 1


@pytest.mark.anyio
async def test_a_database_without_relations_imports_as_before(db_session):
    user = await _connected_user(db_session)
    await _scan(db_session, user, _page("page-call", "Call the bank"))

    await _import(db_session, user, "page-call")

    call = await _task_for(db_session, user, "page-call")
    assert (call.source, call.parent_task_id) == ("notion", None)
    assert await TaskPrerequisiteRepository(db_session).edges_for_user(user.id) == []


# ── What the app sees ─────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_pending_sub_items_name_their_parent_and_offer_import_both(client, db_session):
    user = await _connected_user(db_session)
    await _scan(db_session, user, _page("page-passport", "Renew passport"),
                _page("page-photos", "Get photos", parent="page-passport"))
    passport_item = (await NotionImportItemRepository(db_session).by_pages(user.id, ["page-passport"]))["page-passport"]

    with _signed_in():
        before = {i["page_id"]: i for i in (await client.get("/api/v1/notion/pending", headers=HEADERS)).json()}
    assert before["page-photos"]["parent_title_hint"] == "Renew passport"
    assert before["page-photos"]["parent_pending_item_id"] == str(passport_item.id)
    assert before["page-passport"]["parent_title_hint"] is None

    await _import(db_session, user, "page-passport")
    with _signed_in():
        after = {i["page_id"]: i for i in (await client.get("/api/v1/notion/pending", headers=HEADERS)).json()}
    assert after["page-photos"]["parent_title_hint"] == "Renew passport"
    assert after["page-photos"]["parent_pending_item_id"] is None


class _Model:
    def __init__(self, reply):
        self.reply = reply

    @property
    def name(self):
        return "mock"

    @property
    def default_model(self):
        return "mock-model"

    async def complete(self, request):
        return LLMResponse(content=json.dumps(self.reply), model="mock-model", provider="mock")


@pytest.mark.anyio
async def test_an_import_with_no_notion_parent_may_suggest_one_and_never_applies_it(client, db_session):
    user = await _connected_user(db_session)
    passport = Task(user_id=user.id, title="Renew passport", status="pending")
    db_session.add(passport)
    await db_session.flush()
    await _scan(db_session, user, _page("page-appt", "Book passport photo appointment"))
    item = (await NotionImportItemRepository(db_session).by_pages(user.id, ["page-appt"]))["page-appt"]

    set_llm_gateway(LLMGateway(provider=_Model({"task_id": str(passport.id)})))
    try:
        with _signed_in():
            r = await client.post(f"/api/v1/notion/items/{item.id}/import", headers=HEADERS)
    finally:
        set_llm_gateway(None)  # type: ignore[arg-type]

    assert r.status_code == 200
    assert r.json()["suggested_parent"] == {"id": str(passport.id), "title": "Renew passport"}
    appointment = await _task_for(db_session, user, "page-appt")
    assert appointment.parent_task_id is None
