"""TIME-118 — /now/recommendation returns the full engine decision (any domain) with LLM text."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.security import TokenUser

USER = TokenUser(uid="rec-1", email="rec@example.com", role="user", email_verified=True)


def _verify():
    return patch("app.core.security.firebase_auth.verify_id_token",
                 return_value={"uid": USER.uid, "email": USER.email, "role": "user",
                               "email_verified": True})


@pytest.mark.anyio
async def test_recommendation_for_task_includes_related_task_id(client, db_session):
    from app.services.user_service import UserService
    from app.models.task import Task

    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    # Overdue + top priority → wins regardless of time of day (not time-flaky).
    task = Task(user_id=user.id, title="Finish the deck", status="pending", priority=1,
                due_at=datetime.now(timezone.utc) - timedelta(hours=1), estimated_minutes=40)
    db_session.add(task)
    await db_session.flush()

    with _verify():
        r = await client.get("/api/v1/now/recommendation", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    body = r.json()
    assert body["domain"] == "task"
    assert body["related_task_id"] == str(task.id)
    assert body["title"] and body["explanation"] and body["reason_codes"]
    assert 0.0 <= body["confidence"] <= 1.0 and 0.0 <= body["score"] <= 100.0
    assert isinstance(body["eligible_for_push"], bool)
    # Confidence is derived from the score (single source of truth), not a hardcoded literal.
    from app.services.recommendation.scoring.score import score_to_confidence
    assert body["confidence"] == score_to_confidence(body["score"])


@pytest.mark.anyio
async def test_recommendation_can_be_a_non_task_action(client, db_session):
    """With no tasks, the engine can still recommend a cross-domain action (planning/fallback/…),
    with no related task id."""
    from app.services.user_service import UserService
    await UserService(db_session).get_or_create_user(USER.uid, USER.email)

    with _verify():
        r = await client.get("/api/v1/now/recommendation", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    body = r.json()
    assert body["domain"] in ("planning", "fallback", "health", "routine", "context_switch", "calendar")
    assert body["related_task_id"] is None
    assert body["reason_codes"]


@pytest.mark.anyio
async def test_recommendation_unauthenticated(client):
    r = await client.get("/api/v1/now/recommendation")
    assert r.status_code == 401
