"""TIME-323: every surface that picks a task respects steps and waits.

Now, the legacy recommendations list, the swap, proactive push, the voice assistant and scheduling each
choose tasks on their own path, so each one is checked here rather than trusting a shared filter.
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.security import TokenUser
from app.models.task import Task
from app.repositories.recommendation_swap_repository import RecommendationSwapRepository
from app.repositories.task_prerequisite_repository import TaskPrerequisiteRepository
from app.services.recommendation.context_builder import _to_task_item
from app.services.task_autoschedule import autoschedule_task
from app.services.user_service import UserService

USER = TokenUser(uid="uid-graph-engine", email="graph-engine@example.com", role="user", email_verified=True)
HEADERS = {"Authorization": "Bearer test-token"}
# A fixed weekday mid-morning, inside the default 08–21 working window.
NOW = datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc)


def _signed_in():
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": USER.uid, "email": USER.email, "role": "user", "email_verified": True},
    )


async def _user(db_session):
    row, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    return row


async def _task(db_session, user, title, **fields):
    fields.setdefault("status", "pending")
    task = Task(user_id=user.id, title=title, **fields)
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)
    return task


async def _waits(db_session, user, task, prerequisite):
    await TaskPrerequisiteRepository(db_session).add(user.id, task.id, prerequisite.id)


async def _passport(db_session, user, **parent_fields):
    """Renew passport → Get photos, then Fill out the form."""
    parent = await _task(db_session, user, "Renew passport", steps_sequential=True, **parent_fields)
    photos = await _task(db_session, user, "Get photos", parent_task_id=parent.id, position=0,
                         estimated_minutes=20)
    form = await _task(db_session, user, "Fill out the form", parent_task_id=parent.id, position=1,
                       estimated_minutes=30)
    await TaskPrerequisiteRepository(db_session).rechain_steps(parent)
    return parent, photos, form


async def _now(client):
    with _signed_in():
        r = await client.get("/api/v1/now", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    shown = ([body["best_task"]] if body["best_task"] else []) + body["alternatives"]
    return body, [t["title"] for t in shown]


# ── Now ───────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_now_never_recommends_a_task_that_is_still_waiting(client, db_session):
    user = await _user(db_session)
    invoice = await _task(db_session, user, "Get invoice", priority=4)
    pay = await _task(db_session, user, "Pay contractor", priority=1,
                      due_at=datetime.now(timezone.utc) + timedelta(hours=2))
    await _waits(db_session, user, pay, invoice)

    body, shown = await _now(client)

    assert body["best_task"]["title"] == "Get invoice"
    assert "Pay contractor" not in shown


@pytest.mark.anyio
async def test_now_recommends_the_next_step_and_names_its_parent(client, db_session):
    user = await _user(db_session)
    await _passport(db_session, user, priority=1)

    body, shown = await _now(client)

    assert shown == ["Get photos"]
    best = body["best_task"]
    assert (best["parent_title"], best["position"]) == ("Renew passport", 0)


@pytest.mark.anyio
async def test_a_pinned_task_that_is_waiting_is_not_forced_to_the_top(client, db_session):
    user = await _user(db_session)
    write = await _task(db_session, user, "Write the report")
    send = await _task(db_session, user, "Send the report")
    await _waits(db_session, user, send, write)
    await RecommendationSwapRepository(db_session).create(
        user.id, rejected_task_id=write.id, chosen_task_id=send.id, pin=True
    )

    body, shown = await _now(client)

    assert body["best_task"]["title"] == "Write the report"
    assert "Send the report" not in shown


# ── Swap and the legacy recommendations list ──────────────────────────────────

@pytest.mark.anyio
async def test_swapping_to_a_waiting_task_or_a_parent_is_refused(client, db_session):
    user = await _user(db_session)
    write = await _task(db_session, user, "Write the report")
    send = await _task(db_session, user, "Send the report")
    await _waits(db_session, user, send, write)
    parent, photos, _form = await _passport(db_session, user)

    with _signed_in():
        to_waiting = await client.post("/api/v1/recommendations/swap", headers=HEADERS, json={
            "rejected_task_id": str(write.id), "chosen_task_id": str(send.id)})
        to_parent = await client.post("/api/v1/recommendations/swap", headers=HEADERS, json={
            "rejected_task_id": str(write.id), "chosen_task_id": str(parent.id)})
        to_step = await client.post("/api/v1/recommendations/swap", headers=HEADERS, json={
            "rejected_task_id": str(write.id), "chosen_task_id": str(photos.id)})

    assert to_waiting.status_code == 409 and "Write the report" in to_waiting.json()["detail"]
    assert to_parent.status_code == 409
    assert to_step.status_code == 201


@pytest.mark.anyio
async def test_the_recommendations_list_skips_waiting_tasks_and_parents(client, db_session):
    from app.llm.gateway import LLMGateway, _NoOpProvider, set_llm_gateway

    user = await _user(db_session)
    invoice = await _task(db_session, user, "Get invoice", priority=4)
    pay = await _task(db_session, user, "Pay contractor", priority=1)
    await _waits(db_session, user, pay, invoice)
    await _passport(db_session, user, priority=1)

    set_llm_gateway(LLMGateway(provider=_NoOpProvider()))
    try:
        with _signed_in():
            r = await client.get("/api/v1/recommendations", headers=HEADERS)
    finally:
        set_llm_gateway(None)  # type: ignore[arg-type]

    assert r.status_code == 200
    body = r.json()
    shown = [body["best"]["task"]] + body["alternatives"]
    titles = {t["title"] for t in shown}
    assert "Pay contractor" not in titles and "Renew passport" not in titles
    assert "Fill out the form" not in titles
    assert {"Get invoice", "Get photos"} <= titles
    photos = next(t for t in shown if t["title"] == "Get photos")
    assert photos["parent_title"] == "Renew passport"


# ── Proactive push and voice ──────────────────────────────────────────────────

class _StubSender:
    def __init__(self):
        self.sent = []

    @property
    def available(self):
        return True

    async def send(self, token, title, body, collapse_id=None, data=None):
        self.sent.append((token, title, body, collapse_id, data))
        return True


@pytest.mark.anyio
async def test_the_time_block_offer_skips_waiting_tasks_and_names_a_steps_parent(db_session):
    from app.repositories.device_token_repository import DeviceTokenRepository
    from app.services.push.push_service import ProactivePushService

    user = await _user(db_session)
    await DeviceTokenRepository(db_session).upsert(user.id, "devtok")
    invoice = await _task(db_session, user, "Get invoice", priority=4)
    pay = await _task(db_session, user, "Pay contractor", priority=1, estimated_minutes=30)
    await _waits(db_session, user, pay, invoice)
    parent, photos, _form = await _passport(db_session, user, priority=1)
    photos.priority = 2
    await db_session.flush()

    sender = _StubSender()
    now = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
    offer = await ProactivePushService(db_session).offer_time_block_for_user(user, sender, now=now)

    assert offer is not None
    assert offer["task_id"] == str(photos.id)
    assert offer["title"] == "Block time for “Get photos” (Renew passport)?"
    assert sender.sent[0][4]["parent_title"] == "Renew passport"


@pytest.mark.anyio
async def test_voice_suggests_the_next_step_and_says_what_it_is_for(client, db_session):
    user = await _user(db_session)
    await _passport(db_session, user, priority=1)

    body = {"responseId": "r", "queryResult": {"queryText": "WhatToDoNext",
                                               "intent": {"displayName": "WhatToDoNext"}, "parameters": {}}}
    with _signed_in():
        r = await client.post("/api/v1/assistant/webhook", headers=HEADERS, json=body)

    assert r.status_code == 200
    assert r.json()["fulfillmentText"].startswith("Do Get photos, for Renew passport next.")


# ── Scoring ───────────────────────────────────────────────────────────────────

def test_a_step_scores_with_its_parents_deadline_and_priority():
    owner = uuid.uuid4()
    due = datetime(2026, 9, 18, 17, 0, tzinfo=timezone.utc)
    parent = Task(id=uuid.uuid4(), user_id=owner, title="Renew passport", status="pending", priority=1,
                  due_at=due)
    step = Task(id=uuid.uuid4(), user_id=owner, title="Get photos", status="pending", priority=3,
                parent_task_id=parent.id)

    item = _to_task_item(step, parent)

    assert item.due_date == due.isoformat()
    assert item.priority == "high"


def test_a_steps_own_tighter_deadline_still_wins():
    owner = uuid.uuid4()
    parent_due = datetime(2026, 9, 18, 17, 0, tzinfo=timezone.utc)
    step_due = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
    parent = Task(id=uuid.uuid4(), user_id=owner, title="Renew passport", status="pending", priority=4,
                  due_at=parent_due)
    step = Task(id=uuid.uuid4(), user_id=owner, title="Get photos", status="pending", priority=2,
                due_at=step_due, parent_task_id=parent.id)

    item = _to_task_item(step, parent)

    assert item.due_date == step_due.isoformat()
    assert item.priority == "high"


# ── Scheduling ────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_auto_placement_waits_until_the_prerequisite_ends(db_session):
    user = await _user(db_session)
    invoice = await _task(db_session, user, "Get invoice",
                          scheduled_start=NOW.replace(hour=13), scheduled_end=NOW.replace(hour=14))
    pay = await _task(db_session, user, "Pay contractor", estimated_minutes=30)
    await _waits(db_session, user, pay, invoice)

    assert await autoschedule_task(db_session, pay, now=NOW) is True
    start = pay.scheduled_start if pay.scheduled_start.tzinfo else pay.scheduled_start.replace(tzinfo=timezone.utc)
    assert start >= NOW.replace(hour=14)


@pytest.mark.anyio
async def test_auto_placement_leaves_a_task_untimed_while_its_prerequisite_has_no_time(db_session):
    user = await _user(db_session)
    invoice = await _task(db_session, user, "Get invoice")
    pay = await _task(db_session, user, "Pay contractor", estimated_minutes=30)
    await _waits(db_session, user, pay, invoice)

    assert await autoschedule_task(db_session, pay, now=NOW) is False
    assert pay.scheduled_start is None


@pytest.mark.anyio
async def test_a_step_is_not_placed_before_what_its_parent_waits_for(db_session):
    user = await _user(db_session)
    appointment = await _task(db_session, user, "Book appointment",
                              scheduled_start=NOW.replace(hour=15), scheduled_end=NOW.replace(hour=16))
    parent, photos, _form = await _passport(db_session, user)
    await _waits(db_session, user, parent, appointment)

    assert await autoschedule_task(db_session, photos, now=NOW) is True
    start = photos.scheduled_start if photos.scheduled_start.tzinfo else photos.scheduled_start.replace(tzinfo=timezone.utc)
    assert start >= NOW.replace(hour=16)


@pytest.mark.anyio
async def test_the_suggested_time_comes_after_what_the_task_waits_for(client, db_session):
    user = await _user(db_session)
    tomorrow_noon = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        hour=12, minute=0, second=0, microsecond=0)
    invoice = await _task(db_session, user, "Get invoice", scheduled_start=tomorrow_noon,
                          scheduled_end=tomorrow_noon + timedelta(hours=1))
    pay = await _task(db_session, user, "Pay contractor", estimated_minutes=30)
    await _waits(db_session, user, pay, invoice)

    with _signed_in():
        r = await client.get(f"/api/v1/tasks/{pay.id}/suggested-slot", headers=HEADERS)

    assert r.status_code == 200 and r.json()["fits"] is True
    start = datetime.fromisoformat(r.json()["start"].replace("Z", "+00:00"))
    assert start >= tomorrow_noon + timedelta(hours=1)


@pytest.mark.anyio
async def test_no_time_is_suggested_while_the_prerequisite_has_none(client, db_session):
    user = await _user(db_session)
    invoice = await _task(db_session, user, "Get invoice")
    pay = await _task(db_session, user, "Pay contractor", estimated_minutes=30)
    await _waits(db_session, user, pay, invoice)

    with _signed_in():
        r = await client.get(f"/api/v1/tasks/{pay.id}/suggested-slot", headers=HEADERS)

    assert r.status_code == 200
    assert r.json()["fits"] is False and "Get invoice" in r.json()["message"]
