from unittest.mock import patch

import pytest

from app.core.security import TokenUser

MOCK_USER = TokenUser(uid="test-uid-123", email="test@example.com", role="user", email_verified=True)
MOCK_ADMIN = TokenUser(uid="admin-uid-456", email="admin@example.com", role="admin", email_verified=True)


def _make_decoded(user: TokenUser) -> dict:
    return {
        "uid": user.uid,
        "email": user.email,
        "role": user.role,
        "email_verified": user.email_verified,
    }


@pytest.mark.anyio
async def test_get_me_returns_user_info(client):
    with patch("app.core.security.firebase_auth.verify_id_token", return_value=_make_decoded(MOCK_USER)):
        response = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    data = response.json()
    assert data["uid"] == "test-uid-123"
    assert data["email"] == "test@example.com"
    assert data["role"] == "user"
    assert data["email_verified"] is True


@pytest.mark.anyio
async def test_get_me_without_token_returns_401(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_me_with_invalid_token_returns_401(client):
    from firebase_admin.auth import InvalidIdTokenError

    with patch(
        "app.core.security.firebase_auth.verify_id_token",
        side_effect=InvalidIdTokenError("bad token"),
    ):
        response = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer bad-token"})
    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_me_with_expired_token_returns_401(client):
    from firebase_admin.auth import ExpiredIdTokenError

    with patch(
        "app.core.security.firebase_auth.verify_id_token",
        side_effect=ExpiredIdTokenError("expired", None),
    ):
        response = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer expired-token"})
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_admin_role_returned_correctly(client):
    with patch("app.core.security.firebase_auth.verify_id_token", return_value=_make_decoded(MOCK_ADMIN)):
        response = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer admin-token"})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
