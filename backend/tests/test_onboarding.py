from unittest.mock import patch

import pytest

from app.core.security import TokenUser

MOCK_USER = TokenUser(uid="uid-onboard-1", email="onboard@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


@pytest.mark.anyio
async def test_get_personality_default(client):
    with _mock_verify(MOCK_USER):
        r = await client.get("/api/v1/onboarding/personality", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json()["style"] == "calm_premium"


@pytest.mark.anyio
async def test_set_personality(client):
    with _mock_verify(MOCK_USER):
        r = await client.put(
            "/api/v1/onboarding/personality",
            headers=_auth_headers(),
            json={"style": "high_performance_coach"},
        )
    assert r.status_code == 200
    assert r.json()["style"] == "high_performance_coach"


@pytest.mark.anyio
async def test_set_personality_invalid_rejected(client):
    with _mock_verify(MOCK_USER):
        r = await client.put(
            "/api/v1/onboarding/personality",
            headers=_auth_headers(),
            json={"style": "aggressive_drill_sergeant"},
        )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_get_onboarding_state_default(client):
    with _mock_verify(MOCK_USER):
        r = await client.get("/api/v1/onboarding/state", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["current_step"] == "welcome"
    assert data["chosen_path"] is None
    assert data["completed_steps"] == {}
    assert data["skipped_integrations"] is False


@pytest.mark.anyio
async def test_advance_onboarding_step(client):
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/onboarding/state/advance",
            headers=_auth_headers(),
            json={"next_step": "path_selection"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["current_step"] == "path_selection"
    assert data["completed_steps"].get("welcome") is True


@pytest.mark.anyio
async def test_advance_invalid_step_rejected(client):
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/onboarding/state/advance",
            headers=_auth_headers(),
            json={"next_step": "not_a_real_step"},
        )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_set_onboarding_path(client):
    with _mock_verify(MOCK_USER):
        r = await client.patch(
            "/api/v1/onboarding/state/path",
            headers=_auth_headers(),
            json={"chosen_path": "athlete"},
        )
    assert r.status_code == 200
    assert r.json()["chosen_path"] == "athlete"


@pytest.mark.anyio
async def test_complete_onboarding(client):
    with _mock_verify(MOCK_USER):
        r = await client.post("/api/v1/onboarding/state/complete", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json()["current_step"] == "complete"
