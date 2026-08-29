"""Tests for privacy data export + account deletion (TIME-055)."""
import json
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


@pytest.mark.anyio
async def test_export_and_delete_cover_recommendation_events(client, db_session):
    """recommendation_events are in the export bundle and removed on account deletion (TIME-200)."""
    from sqlalchemy import select

    from app.models.recommendation_event import RecommendationEvent
    from app.models.task import Task
    from app.repositories.recommendation_event_repository import RecommendationEventRepository
    from app.services.user_service import UserService

    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    user_id = user.id
    task = Task(user_id=user.id, title="T", status="pending")
    db_session.add(task)
    await db_session.flush()
    await RecommendationEventRepository(db_session).record_impression(user.id, task.id, surface="now", confidence=0.8)
    await db_session.commit()

    with _mock_verify(USER):
        r = await client.get("/api/v1/privacy/export", headers=_auth_headers())
    assert r.status_code == 200
    assert len(r.json()["recommendation_events"]) == 1

    with _mock_verify(USER):
        d = await client.delete("/api/v1/privacy/account?confirm=true", headers=_auth_headers())
    assert d.status_code == 204
    remaining = (
        await db_session.execute(
            select(RecommendationEvent).where(RecommendationEvent.user_id == user_id)
        )
    ).scalars().all()
    assert remaining == []


# ── TIME-304: the export must not drift behind the schema again ──────────────────────────


def test_every_user_scoped_table_is_in_the_export():
    """The export had drifted badly: an audit found FIFTEEN user-scoped tables missing, not the two
    the ticket assumed. Privacy policy section 8 promises "a portable copy of all your data", so a
    table that stores something about a user and isn't here is a broken promise.

    This test is the guard — add a user-scoped table without adding it to _USER_DATA and it fails.
    """
    from app.models.base import Base
    from app.services.privacy_service import _USER_DATA

    exported = {model.__tablename__ for _, model, _ in _USER_DATA}
    missing = sorted(
        mapper.class_.__tablename__
        for mapper in Base.registry.mappers
        if "user_id" in {c.name for c in mapper.columns}
        and mapper.class_.__tablename__ not in exported
    )
    assert missing == [], (
        f"these user-scoped tables are missing from the privacy export: {missing}. "
        "Add them to _USER_DATA in privacy_service.py."
    )


def test_credentials_are_redacted_but_the_users_own_data_is_not():
    """An export gets emailed, synced and shared, so a live credential inside one is a real leak —
    even though the user requested it themselves.

    Location coordinates are deliberately NOT redacted: they are the user's own data, and handing
    it back is the entire point of the export.
    """
    from app.services.privacy_service import _REDACTED_COLUMNS

    assert "access_token" in _REDACTED_COLUMNS
    assert "refresh_token" in _REDACTED_COLUMNS
    # The APNs push token — a credential, and it was NOT covered before TIME-304.
    assert "token" in _REDACTED_COLUMNS
    assert "latitude" not in _REDACTED_COLUMNS
    assert "longitude" not in _REDACTED_COLUMNS


@pytest.mark.anyio
async def test_a_recorded_duration_observation_appears_in_the_export(db_session):
    """End to end for the table that prompted this: TIME-286 added it and did not add it here."""
    from app.services.privacy_service import PrivacyService
    from app.services.task_duration_service import TaskDurationEstimator
    from app.services.user_service import UserService

    user, _ = await UserService(db_session).get_or_create_user("uid-exp", "exp@example.com")
    await TaskDurationEstimator(db_session).record_actual(
        user.id, "Buy groceries", 42, estimated_minutes=30
    )
    await db_session.flush()

    bundle = await PrivacyService(db_session).export_data(user.id)

    assert "task_duration_observations" in bundle
    assert any(row["actual_minutes"] == 42 for row in bundle["task_duration_observations"])
    assert "task_duration_estimates" in bundle
    assert bundle["task_duration_estimates"], "the learned estimate should be exported too"


@pytest.mark.anyio
async def test_a_push_token_is_never_exported_in_the_clear(db_session):
    from app.models.device_token import DeviceToken
    from app.services.privacy_service import PrivacyService
    from app.services.user_service import UserService

    user, _ = await UserService(db_session).get_or_create_user("uid-tok", "tok@example.com")
    db_session.add(DeviceToken(user_id=user.id, token="SECRET-APNS-TOKEN", platform="ios"))
    await db_session.flush()

    bundle = await PrivacyService(db_session).export_data(user.id)
    rows = bundle["device_tokens"]
    assert rows, "the device token row should still be exported"
    assert rows[0]["token"] == "[redacted]"
    assert "SECRET-APNS-TOKEN" not in json.dumps(bundle)
