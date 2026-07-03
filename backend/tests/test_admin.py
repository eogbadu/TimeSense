from unittest.mock import patch

import pytest

from app.core.security import TokenUser

ADMIN_USER = TokenUser(uid="uid-admin-1", email="admin@timesense.app", role="admin", email_verified=True)
NORMAL_USER = TokenUser(uid="uid-normal-1", email="user@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


@pytest.mark.anyio
async def test_admin_health_accessible_to_admin(client):
    with _mock_verify(ADMIN_USER):
        r = await client.get("/api/v1/admin/health", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


@pytest.mark.anyio
async def test_admin_health_forbidden_to_normal_user(client):
    with _mock_verify(NORMAL_USER):
        r = await client.get("/api/v1/admin/health", headers=_auth_headers())
    assert r.status_code == 403


@pytest.mark.anyio
async def test_admin_health_unauthenticated(client):
    r = await client.get("/api/v1/admin/health")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_admin_list_users(client):
    # Seed a normal user first
    with _mock_verify(NORMAL_USER):
        await client.get("/api/v1/users/me", headers=_auth_headers())

    with _mock_verify(ADMIN_USER):
        r = await client.get("/api/v1/admin/users", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert "users" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.anyio
async def test_admin_list_users_forbidden_to_normal_user(client):
    with _mock_verify(NORMAL_USER):
        r = await client.get("/api/v1/admin/users", headers=_auth_headers())
    assert r.status_code == 403


@pytest.mark.anyio
async def test_admin_list_users_pagination(client):
    with _mock_verify(ADMIN_USER):
        r = await client.get("/api/v1/admin/users?offset=0&limit=5", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["limit"] == 5
    assert data["offset"] == 0
