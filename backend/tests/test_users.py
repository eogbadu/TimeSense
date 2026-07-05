from unittest.mock import patch

import pytest

from app.core.security import TokenUser

MOCK_USER = TokenUser(uid="uid-abc", email="user@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


@pytest.mark.anyio
async def test_get_me_creates_user_on_first_call(client):
    with _mock_verify(MOCK_USER):
        response = await client.get("/api/v1/users/me", headers=_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"
    assert data["role"] == "user"
    assert data["onboarding_complete"] is False
    assert data["profile"] is not None
    assert data["preferences"] is not None


@pytest.mark.anyio
async def test_get_me_returns_same_user_on_repeat_calls(client):
    with _mock_verify(MOCK_USER):
        r1 = await client.get("/api/v1/users/me", headers=_auth_headers())
        r2 = await client.get("/api/v1/users/me", headers=_auth_headers())
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.anyio
async def test_update_profile(client):
    with _mock_verify(MOCK_USER):
        await client.get("/api/v1/users/me", headers=_auth_headers())
        response = await client.patch(
            "/api/v1/users/me/profile",
            headers=_auth_headers(),
            json={"display_name": "Ekele", "timezone": "America/New_York"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Ekele"
    assert data["timezone"] == "America/New_York"


@pytest.mark.anyio
async def test_update_preferences(client):
    with _mock_verify(MOCK_USER):
        await client.get("/api/v1/users/me", headers=_auth_headers())
        response = await client.patch(
            "/api/v1/users/me/preferences",
            headers=_auth_headers(),
            json={"notification_mode": "balanced", "theme": "dark"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["notification_mode"] == "balanced"
    assert data["theme"] == "dark"


@pytest.mark.anyio
async def test_update_preferences_invalid_mode_rejected(client):
    with _mock_verify(MOCK_USER):
        await client.get("/api/v1/users/me", headers=_auth_headers())
        response = await client.patch(
            "/api/v1/users/me/preferences",
            headers=_auth_headers(),
            json={"notification_mode": "invalid_mode"},
        )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_unauthenticated_request_rejected(client):
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


# ── Role sync from Firebase token claim (TIME-065) ────────────────────────────

_ADMIN_USER = TokenUser(uid="uid-admin-1", email="admin@example.com", role="admin", email_verified=True)


@pytest.mark.anyio
async def test_get_me_reflects_admin_token_claim(client):
    """A fresh user whose token claim is admin comes back as role=admin from /users/me."""
    with _mock_verify(_ADMIN_USER):
        r = await client.get("/api/v1/users/me", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


@pytest.mark.anyio
async def test_get_me_syncs_role_downgrade_when_claim_removed(client):
    """DB role mirrors the claim: granting then removing the admin claim downgrades the DB role."""
    user = TokenUser(uid="uid-sync-1", email="sync@example.com", role="admin", email_verified=True)
    with _mock_verify(user):
        r1 = await client.get("/api/v1/users/me", headers=_auth_headers())
    assert r1.json()["role"] == "admin"

    # Same user, claim removed (defaults to "user")
    downgraded = TokenUser(uid="uid-sync-1", email="sync@example.com", role="user", email_verified=True)
    with _mock_verify(downgraded):
        r2 = await client.get("/api/v1/users/me", headers=_auth_headers())
    assert r2.json()["id"] == r1.json()["id"]
    assert r2.json()["role"] == "user"
