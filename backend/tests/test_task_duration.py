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
