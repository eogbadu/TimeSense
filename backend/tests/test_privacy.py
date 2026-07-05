"""Tests for privacy data export + account deletion (TIME-055)."""
from unittest.mock import patch

import pytest

from app.core.security import TokenUser
from app.models.calendar import CalendarIntegration
from app.models.consent import ConsentRecord
from app.models.task import Task
from app.services.user_service import UserService

USER = TokenUser(uid="uid-privacy-1", email="p1@example.com", role="user", email_verified=True)
OTHER = TokenUser(uid="uid-privacy-2", email="p2@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


async def _seed_user_with_data(db_session, user: TokenUser):
    row, _ = await UserService(db_session).get_or_create_user(user.uid, user.email)
    db_session.add(Task(user_id=row.id, title="Write spec", status="pending", priority=2))
    db_session.add(ConsentRecord(user_id=row.id, consent_type="analytics", granted=True))
    db_session.add(CalendarIntegration(user_id=row.id, provider="google", access_token="secret-token-123"))
    await db_session.flush()
    return row


# ── Export ────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_export_includes_user_data(client, db_session):
    await _seed_user_with_data(db_session, USER)
    with _mock_verify(USER):
        r = await client.get("/api/v1/privacy/export", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["user"]["email"] == USER.email
    assert len(data["tasks"]) == 1 and data["tasks"][0]["title"] == "Write spec"
    assert len(data["consent_records"]) == 1
    assert "exported_at" in data


@pytest.mark.anyio
async def test_export_redacts_tokens(client, db_session):
    await _seed_user_with_data(db_session, USER)
    with _mock_verify(USER):
        r = await client.get("/api/v1/privacy/export", headers=_auth_headers())
    integrations = r.json()["calendar_integrations"]
    assert len(integrations) == 1
    assert integrations[0]["access_token"] == "[redacted]"
    assert "secret-token-123" not in r.text


@pytest.mark.anyio
async def test_export_requires_auth(client):
    r = await client.get("/api/v1/privacy/export")
    assert r.status_code == 401


# ── Deletion ──────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_delete_account_erases_user_and_cascades(client, db_session):
    user = await _seed_user_with_data(db_session, USER)
    user_id = user.id
    with _mock_verify(USER):
        r = await client.delete("/api/v1/privacy/account?confirm=true", headers=_auth_headers())
    assert r.status_code == 204

    from app.models.user import User
    from sqlalchemy import select
    assert (await db_session.execute(select(User).where(User.id == user_id))).scalar_one_or_none() is None
    # cascade removed owned rows
    assert (await db_session.execute(select(Task).where(Task.user_id == user_id))).scalars().all() == []
    assert (await db_session.execute(select(ConsentRecord).where(ConsentRecord.user_id == user_id))).scalars().all() == []


@pytest.mark.anyio
async def test_delete_requires_confirm(client, db_session):
    await _seed_user_with_data(db_session, USER)
    with _mock_verify(USER):
        r = await client.delete("/api/v1/privacy/account", headers=_auth_headers())
    assert r.status_code == 400

    from app.models.user import User
    from sqlalchemy import select
    assert (await db_session.execute(select(User).where(User.firebase_uid == USER.uid))).scalar_one_or_none() is not None


@pytest.mark.anyio
async def test_delete_only_affects_own_data(client, db_session):
    await _seed_user_with_data(db_session, USER)
    other = await _seed_user_with_data(db_session, OTHER)
    with _mock_verify(USER):
        r = await client.delete("/api/v1/privacy/account?confirm=true", headers=_auth_headers())
    assert r.status_code == 204

    from sqlalchemy import select
    others_tasks = (await db_session.execute(select(Task).where(Task.user_id == other.id))).scalars().all()
    assert len(others_tasks) == 1  # the other user's data is untouched


@pytest.mark.anyio
async def test_delete_requires_auth(client):
    r = await client.delete("/api/v1/privacy/account?confirm=true")
    assert r.status_code == 401
