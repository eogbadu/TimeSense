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


@pytest.mark.anyio
async def test_test_push_reports_apns_unavailable_without_creds(client, db_session):
    """With no APNs creds, test-push returns apns_available=false and delivers nothing — but the
    endpoint still works (so the user knows the server needs credentials)."""
    from app.services.user_service import UserService
    from app.services.push.sender import NullPushSender
    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    # Pin the sender so the test doesn't depend on whether this machine's .env has APNs creds.
    with _verify(), patch("app.api.v1.devices.get_push_sender", return_value=NullPushSender()):
        await client.put("/api/v1/devices", headers={"Authorization": "Bearer t"},
                         json={"token": "tok-test-push"})
        r = await client.post("/api/v1/devices/test-push", headers={"Authorization": "Bearer t"},
                              json={"title": "Hi", "body": "This is a test."})
    assert r.status_code == 200
    body = r.json()
    assert body["apns_available"] is False and body["delivered"] == 0
    assert body["title"] == "Hi" and body["body"] == "This is a test."


@pytest.mark.anyio
async def test_test_push_no_device(client, db_session):
    from app.services.user_service import UserService
    await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    with _verify():
        r = await client.post("/api/v1/devices/test-push", headers={"Authorization": "Bearer t"},
                              json={})
    assert r.status_code == 200 and r.json()["reason"] == "no_device"
