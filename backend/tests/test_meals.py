from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.core.security import TokenUser

MOCK_USER = TokenUser(uid="uid-meal-1", email="meal@example.com", role="user", email_verified=True)
OTHER_USER = TokenUser(uid="uid-meal-2", email="meal-other@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


@pytest.mark.anyio
async def test_log_meal(client):
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/meals",
            headers=_auth_headers(),
            json={"meal_type": "lunch", "status": "eaten"},
        )
    assert r.status_code == 201
    data = r.json()
    assert data["meal_type"] == "lunch"
    assert data["status"] == "eaten"


@pytest.mark.anyio
async def test_today_status_reflects_explicit_log_via_api(client):
    with _mock_verify(MOCK_USER):
        await client.post(
            "/api/v1/meals",
            headers=_auth_headers(),
            json={"meal_type": "breakfast", "status": "eaten"},
        )
        r = await client.get("/api/v1/meals/today", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json()["breakfast"] == "eaten"


@pytest.mark.anyio
async def test_explicit_log_overrides_inference(client):
    with _mock_verify(MOCK_USER):
        await client.post(
            "/api/v1/meals",
            headers=_auth_headers(),
            json={"meal_type": "dinner", "status": "eating_while_working"},
        )
        r = await client.get("/api/v1/meals/today", headers=_auth_headers())
    assert r.json()["dinner"] == "eating_while_working"


@pytest.mark.anyio
async def test_meals_are_per_user(client):
    with _mock_verify(MOCK_USER):
        await client.post(
            "/api/v1/meals",
            headers=_auth_headers(),
            json={"meal_type": "lunch", "status": "eaten"},
        )
    with _mock_verify(OTHER_USER):
        r = await client.get("/api/v1/meals/today", headers=_auth_headers())
    assert r.json()["lunch"] != "eaten"


@pytest.mark.anyio
async def test_invalid_meal_type_422(client):
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/meals",
            headers=_auth_headers(),
            json={"meal_type": "brunch", "status": "eaten"},
        )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_invalid_status_422(client):
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/meals",
            headers=_auth_headers(),
            json={"meal_type": "lunch", "status": "delicious"},
        )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_meals_unauthenticated(client):
    r = await client.get("/api/v1/meals/today")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_repository_infers_skipped_after_window_passes(db_session):
    """Direct repository test: a meal window that has fully elapsed with no log infers 'skipped'."""
    from app.models.user import User
    from app.repositories.meal_repository import MealRepository

    user = User(firebase_uid="uid-meal-repo", email="meal-repo@example.com")
    db_session.add(user)
    await db_session.flush()

    # Anchor "now" well after the default lunch window (12:00-12:30 UTC) ends.
    now = datetime.now(timezone.utc).replace(hour=15, minute=0, second=0, microsecond=0)
    status = await MealRepository(db_session).get_today_status(user.id, now)
    assert status["lunch"] == "skipped"


@pytest.mark.anyio
async def test_repository_pending_before_window_ends(db_session):
    from app.models.user import User
    from app.repositories.meal_repository import MealRepository

    user = User(firebase_uid="uid-meal-repo-2", email="meal-repo-2@example.com")
    db_session.add(user)
    await db_session.flush()

    now = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
    status = await MealRepository(db_session).get_today_status(user.id, now)
    assert status["lunch"] == "pending"
