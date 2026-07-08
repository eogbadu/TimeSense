"""TIME-121 — device token registration."""

from unittest.mock import patch

import pytest

from app.core.security import TokenUser

USER = TokenUser(uid="dev-1", email="dev@example.com", role="user", email_verified=True)


def _verify():
    return patch("app.core.security.firebase_auth.verify_id_token",
                 return_value={"uid": USER.uid, "email": USER.email, "role": "user",
                               "email_verified": True})


@pytest.mark.anyio
async def test_register_and_reregister_device_token(client, db_session):
    from app.services.user_service import UserService
    from app.repositories.device_token_repository import DeviceTokenRepository

    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    with _verify():
        r = await client.put("/api/v1/devices", headers={"Authorization": "Bearer t"},
                             json={"token": "abc123token", "platform": "ios"})
        assert r.status_code == 200 and r.json()["ok"] is True
        # re-registering the same token is idempotent
        await client.put("/api/v1/devices", headers={"Authorization": "Bearer t"},
                         json={"token": "abc123token", "platform": "ios"})

    tokens = await DeviceTokenRepository(db_session).list_tokens(user.id)
    assert tokens == ["abc123token"]


@pytest.mark.anyio
async def test_unregister_device_token(client, db_session):
    from app.services.user_service import UserService
    from app.repositories.device_token_repository import DeviceTokenRepository

    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    with _verify():
        await client.put("/api/v1/devices", headers={"Authorization": "Bearer t"},
                         json={"token": "tok-xyz"})
        d = await client.delete("/api/v1/devices/tok-xyz", headers={"Authorization": "Bearer t"})
        assert d.status_code == 200
    assert await DeviceTokenRepository(db_session).list_tokens(user.id) == []


@pytest.mark.anyio
async def test_register_requires_auth(client):
    r = await client.put("/api/v1/devices", json={"token": "abc123token"})
    assert r.status_code == 401
