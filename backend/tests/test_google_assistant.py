"""
Tests for the Google Assistant / Dialogflow fulfillment webhook (TIME-053).

Uses the shared client/db_session fixtures. The webhook is gated on the Firebase identity (the
account-linked stand-in), so tests mock verify_id_token like every other authed endpoint.
"""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.core.security import TokenUser
from app.models.task import Task
from app.services.user_service import UserService

MOCK_USER = TokenUser(uid="uid-ga-1", email="ga@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser = MOCK_USER):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


def _dialogflow_body(intent: str) -> dict:
    return {
        "responseId": "abc",
        "queryResult": {
            "queryText": intent,
            "intent": {"displayName": intent},
            "parameters": {},
        },
    }


def _fulfillment_text(resp_json: dict) -> str:
    return resp_json["fulfillmentText"]


async def _seed_user(db_session, user: TokenUser = MOCK_USER):
    row, _ = await UserService(db_session).get_or_create_user(user.uid, user.email)
    return row


async def _seed_task(db_session, user_row, title="Write the report", status="pending"):
    task = Task(user_id=user_row.id, title=title, status=status, priority=2)
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)
    return task


# ── Auth ──────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_webhook_requires_auth(client):
    r = await client.post("/api/v1/assistant/webhook", json=_dialogflow_body("WhatToDoNext"))
    assert r.status_code == 401


# ── WhatToDoNext ──────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_what_to_do_next_returns_best_task(client, db_session):
    user = await _seed_user(db_session)
    await _seed_task(db_session, user, title="Write the report")
    with _mock_verify():
        r = await client.post("/api/v1/assistant/webhook", headers=_auth_headers(),
                              json=_dialogflow_body("WhatToDoNext"))
    assert r.status_code == 200
    text = _fulfillment_text(r.json())
    assert "Write the report" in text
    assert "usable time" in text


@pytest.mark.anyio
async def test_what_to_do_next_all_caught_up(client, db_session):
    await _seed_user(db_session)
    with _mock_verify():
        r = await client.post("/api/v1/assistant/webhook", headers=_auth_headers(),
                              json=_dialogflow_body("WhatToDoNext"))
    assert "caught up" in _fulfillment_text(r.json()).lower()


# ── LogLunch (side effect) ────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_log_lunch_logs_a_meal(client, db_session):
    user = await _seed_user(db_session)
    with _mock_verify():
        r = await client.post("/api/v1/assistant/webhook", headers=_auth_headers(),
                              json=_dialogflow_body("LogLunch"))
    assert "lunch" in _fulfillment_text(r.json()).lower()

    from app.repositories.meal_repository import MealRepository
    status = await MealRepository(db_session).get_today_status(user.id)
    assert status.get("lunch") == "eaten"


# ── MarkDone (side effect) ────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_mark_done_completes_best_task(client, db_session):
    user = await _seed_user(db_session)
    task = await _seed_task(db_session, user, title="Ship it")
    with _mock_verify():
        r = await client.post("/api/v1/assistant/webhook", headers=_auth_headers(),
                              json=_dialogflow_body("MarkDone"))
    assert "Ship it" in _fulfillment_text(r.json())

    from app.repositories.task_repository import TaskRepository
    refreshed = await TaskRepository(db_session).get_by_id(task.id, user.id)
    assert refreshed.status == "done"


@pytest.mark.anyio
async def test_mark_done_nothing_to_do(client, db_session):
    await _seed_user(db_session)
    with _mock_verify():
        r = await client.post("/api/v1/assistant/webhook", headers=_auth_headers(),
                              json=_dialogflow_body("MarkDone"))
    assert "nothing to mark done" in _fulfillment_text(r.json()).lower()


# ── StartFocus / ReplanDay ────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_start_focus(client, db_session):
    user = await _seed_user(db_session)
    await _seed_task(db_session, user, title="Deep work")
    with _mock_verify():
        r = await client.post("/api/v1/assistant/webhook", headers=_auth_headers(),
                              json=_dialogflow_body("StartFocus"))
    assert "Deep work" in _fulfillment_text(r.json())


@pytest.mark.anyio
async def test_replan_day_opens_app_not_headless(client, db_session):
    await _seed_user(db_session)
    with _mock_verify():
        r = await client.post("/api/v1/assistant/webhook", headers=_auth_headers(),
                              json=_dialogflow_body("ReplanDay"))
    assert "open timesense" in _fulfillment_text(r.json()).lower()


# ── Intent-name normalization + unknown fallback ──────────────────────────────

@pytest.mark.anyio
async def test_intent_name_is_space_and_case_insensitive(client, db_session):
    user = await _seed_user(db_session)
    await _seed_task(db_session, user, title="Normalized task")
    with _mock_verify():
        r = await client.post("/api/v1/assistant/webhook", headers=_auth_headers(),
                              json=_dialogflow_body("what to do next"))
    assert "Normalized task" in _fulfillment_text(r.json())


@pytest.mark.anyio
async def test_unknown_intent_graceful_fallback(client, db_session):
    await _seed_user(db_session)
    with _mock_verify():
        r = await client.post("/api/v1/assistant/webhook", headers=_auth_headers(),
                              json=_dialogflow_body("OrderPizza"))
    assert r.status_code == 200
    assert "didn't catch that" in _fulfillment_text(r.json()).lower()
