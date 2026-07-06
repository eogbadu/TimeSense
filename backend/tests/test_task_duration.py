"""Tests for the task duration estimator (TIME-082)."""
import pytest

from app.services.task_duration import DEFAULT_DURATIONS, infer_category, seed_duration
from app.services.task_duration_service import TaskDurationEstimator


def test_infer_category():
    assert infer_category("Call the dentist") == "appointment"   # appointment beats call
    assert infer_category("Call mom") == "call"
    assert infer_category("Go to Home Depot") == "shopping"
    assert infer_category("Reply to Sarah's email") == "email"
    assert infer_category("Clean the garage") == "chore"
    assert infer_category("Morning run") == "exercise"
    assert infer_category("Ponder the universe") == "general"


def test_seed_duration_defaults():
    assert seed_duration("call") == DEFAULT_DURATIONS["call"]
    assert seed_duration("nonsense") == DEFAULT_DURATIONS["general"]


@pytest.mark.anyio
async def test_estimate_uses_seed_then_learned(db_session):
    import uuid
    from app.services.user_service import UserService
    from app.core.security import TokenUser

    tu = TokenUser(uid="dur-1", email="dur@example.com", role="user", email_verified=True)
    user, _ = await UserService(db_session).get_or_create_user(tu.uid, tu.email)
    est = TaskDurationEstimator(db_session)

    # Seed value first (no learning yet)
    minutes, category = await est.estimate(user.id, "Buy groceries")
    assert category == "shopping"
    assert minutes == DEFAULT_DURATIONS["shopping"]

    # Teach it that this user's shopping runs long; the estimate should move toward it.
    await est.record_actual(user.id, "Buy groceries", 90)
    learned, _ = await est.estimate(user.id, "Grab milk from the store")  # also "shopping"
    assert learned != DEFAULT_DURATIONS["shopping"]
    assert DEFAULT_DURATIONS["shopping"] < learned <= 90


@pytest.mark.anyio
async def test_capture_fills_estimate_from_lookup(client, db_session):
    """A captured task with no LLM estimate still gets a duration from the lookup table."""
    from unittest.mock import patch

    tu_claims = {"uid": "dur-2", "email": "dur2@example.com", "role": "user", "email_verified": True}
    with patch("app.core.security.firebase_auth.verify_id_token", return_value=tu_claims):
        r = await client.post(
            "/api/v1/capture",
            headers={"Authorization": "Bearer t"},
            json={"raw_input": "Call mom"},  # LLM unavailable in tests → fallback path
        )
    assert r.status_code == 201
    assert r.json()["estimated_minutes"] == DEFAULT_DURATIONS["call"]


@pytest.mark.anyio
async def test_duration_prompt_and_feedback_learns(client, db_session):
    """During the learning period /duration-prompt asks; feedback teaches and eventually stops asking."""
    from unittest.mock import patch
    from app.services.task_duration import DEFAULT_DURATIONS

    claims = {"uid": "dur-3", "email": "dur3@example.com", "role": "user", "email_verified": True}
    with patch("app.core.security.firebase_auth.verify_id_token", return_value=claims):
        # capture a task (shopping) → gets seed estimate
        r = await client.post("/api/v1/capture", headers={"Authorization": "Bearer t"},
                              json={"raw_input": "Buy groceries"})
        task_id = r.json()["id"]

        # prompt should ask (nothing learned yet)
        p = await client.get(f"/api/v1/tasks/{task_id}/duration-prompt", headers={"Authorization": "Bearer t"})
        assert p.status_code == 200 and p.json()["ask"] is True and p.json()["category"] == "shopping"

        # give feedback: it took 90 min → learned estimate moves up
        f = await client.post(f"/api/v1/tasks/{task_id}/duration-feedback",
                              headers={"Authorization": "Bearer t"}, json={"actual_minutes": 90})
        assert f.status_code == 200
        assert f.json()["category"] == "shopping"
        assert f.json()["estimated_minutes"] > DEFAULT_DURATIONS["shopping"]

        # after enough observations, it stops asking
        for _ in range(5):
            await client.post(f"/api/v1/tasks/{task_id}/duration-feedback",
                              headers={"Authorization": "Bearer t"}, json={"actual_minutes": 90})
        p2 = await client.get(f"/api/v1/tasks/{task_id}/duration-prompt", headers={"Authorization": "Bearer t"})
        assert p2.json()["ask"] is False
