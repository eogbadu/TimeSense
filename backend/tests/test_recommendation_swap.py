"""TIME-294 — "not that, THIS instead".

A rejection says a pick was wrong. A swap says what would have been right, in a known context —
a paired preference, which is worth far more for learning than either half alone.

Two properties matter here. The swap must be ADDITIVE (every existing feedback path keeps working
unchanged), and the choice must be HONOURED — recording a preference without acting on it is the
worst of both worlds: the user tells the app what they want and watches it argue back.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.security import TokenUser

USER = TokenUser(uid="uid-swap", email="swap@example.com", role="user", email_verified=True)


def _auth():
    return {"Authorization": "Bearer test-token"}


def _verify(user: TokenUser = USER):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role,
                      "email_verified": user.email_verified},
    )


async def _task(client, title):
    r = await client.post("/api/v1/tasks", headers=_auth(),
                          json={"title": title, "source": "manual"})
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


@pytest.mark.anyio
async def test_a_swap_is_recorded_and_pins_the_chosen_task(client):
    with _verify():
        rejected = await _task(client, "Write the report")
        chosen = await _task(client, "Buy groceries")
        r = await client.post("/api/v1/recommendations/swap", headers=_auth(),
                              json={"rejected_task_id": rejected, "chosen_task_id": chosen,
                                    "reason": "not_priority"})
    assert r.status_code == 201, r.text
    assert r.json()["chosen_task_id"] == chosen
    assert r.json()["pinned_until"] is not None


@pytest.mark.anyio
async def test_the_disagree_is_still_written_through_the_existing_path(client, db_session):
    """Additive, not a replacement — every learning path that already reads
    recommendation_feedback keeps working without knowing swaps exist."""
    from sqlalchemy import select

    from app.models.recommendation_feedback import RecommendationFeedback

    with _verify():
        rejected = await _task(client, "Write the report")
        chosen = await _task(client, "Buy groceries")
        await client.post("/api/v1/recommendations/swap", headers=_auth(),
                          json={"rejected_task_id": rejected, "chosen_task_id": chosen,
                                "reason": "too_big"})

    rows = (await db_session.execute(select(RecommendationFeedback))).scalars().all()
    assert len(rows) == 1
    assert rows[0].signal == "disagree"
    assert rows[0].reason == "too_big"
    assert str(rows[0].task_id) == rejected


@pytest.mark.anyio
async def test_the_context_snapshot_captures_what_cannot_be_reconstructed_later(client, db_session):
    """"Chose an errand over deep work" reads differently at 9am on good sleep than at 8pm when
    depleted. The surrounding state has to be stored with the pair."""
    from sqlalchemy import select

    from app.models.recommendation_swap import RecommendationSwap

    with _verify():
        rejected = await _task(client, "Write the report")
        chosen = await _task(client, "Buy groceries")
        await client.post("/api/v1/recommendations/swap", headers=_auth(),
                          json={"rejected_task_id": rejected, "chosen_task_id": chosen})

    swap = (await db_session.execute(select(RecommendationSwap))).scalar_one()
    snapshot = swap.context_snapshot
    assert snapshot["energy"] in {"low", "medium", "high"}
    assert 0 <= snapshot["local_hour"] <= 23
    assert snapshot["rejected_category"] == "writing"
    assert snapshot["chosen_category"] == "shopping"


@pytest.mark.anyio
async def test_a_task_cannot_be_swapped_for_itself(client):
    with _verify():
        task = await _task(client, "Write the report")
        r = await client.post("/api/v1/recommendations/swap", headers=_auth(),
                              json={"rejected_task_id": task, "chosen_task_id": task})
    assert r.status_code == 400


@pytest.mark.anyio
async def test_another_users_task_cannot_be_swapped_in(client):
    other = TokenUser(uid="uid-swap-2", email="swap2@example.com", role="user", email_verified=True)
    with _verify():
        mine = await _task(client, "Write the report")
    with _verify(other):
        theirs = await _task(client, "Their secret task")
    with _verify():
        r = await client.post("/api/v1/recommendations/swap", headers=_auth(),
                              json={"rejected_task_id": mine, "chosen_task_id": theirs})
    assert r.status_code == 404


@pytest.mark.anyio
async def test_the_pin_expires_on_its_own(db_session):
    from app.repositories.recommendation_swap_repository import (
        PIN_DURATION,
        RecommendationSwapRepository,
    )
    from app.services.user_service import UserService

    from app.models.task import Task

    user, _ = await UserService(db_session).get_or_create_user("uid-pin", "pin@example.com")
    task = Task(user_id=user.id, title="Buy groceries", status="pending", priority=3)
    db_session.add(task)
    await db_session.flush()

    repo = RecommendationSwapRepository(db_session)
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)

    # A swap with no chosen task can't pin anything.
    await repo.create(user.id, rejected_task_id=None, chosen_task_id=None, now=now)
    assert await repo.active_pin(user.id, now) is None

    swap = await repo.create(user.id, rejected_task_id=None, chosen_task_id=task.id, now=now)
    assert swap.pinned_until is not None
    assert await repo.active_pin(user.id, now) is not None
    assert await repo.active_pin(user.id, now + PIN_DURATION + timedelta(minutes=1)) is None


@pytest.mark.anyio
async def test_acting_on_the_pinned_task_releases_the_pin(client, db_session):
    """The pin has done its job once the user acts — it shouldn't keep overriding the engine for
    the rest of its window."""
    from app.repositories.recommendation_swap_repository import RecommendationSwapRepository
    from app.repositories.user_repository import UserRepository

    with _verify():
        rejected = await _task(client, "Write the report")
        chosen = await _task(client, "Buy groceries")
        await client.post("/api/v1/recommendations/swap", headers=_auth(),
                          json={"rejected_task_id": rejected, "chosen_task_id": chosen})

    user = await UserRepository(db_session).get_by_email(USER.email)
    repo = RecommendationSwapRepository(db_session)
    assert await repo.active_pin(user.id) is not None

    with _verify():
        r = await client.post("/api/v1/recommendations/feedback", headers=_auth(),
                              json={"task_id": chosen, "signal": "done"})
    assert r.status_code == 201, r.text
    assert await repo.active_pin(user.id) is None


@pytest.mark.anyio
async def test_the_pinned_task_becomes_the_recommendation(client, db_session):
    """The point of the whole feature: the user says "do this instead" and the app does."""
    with _verify():
        rejected = await _task(client, "Write the report")
        chosen = await _task(client, "Take out the bins")
        await client.post("/api/v1/recommendations/swap", headers=_auth(),
                          json={"rejected_task_id": rejected, "chosen_task_id": chosen})
        now = await client.get("/api/v1/now", headers=_auth())

    assert now.status_code == 200, now.text
    best = now.json().get("best_task")
    assert best is not None, "no recommendation returned"
    assert best["id"] == chosen, f"pinned task was not surfaced; got {best['title']!r}"
