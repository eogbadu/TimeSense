"""
Tests for notification delivery and replan approval flow.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.core.entitlements import require_premium
from app.core.security import TokenUser, get_current_user
from app.main import app
from app.models import (  # noqa: F401
    AssistantPersonality,
    CalendarIntegration,
    ConsentRecord,
    Notification,
    OnboardingState,
    PendingCalendarAction,
    ReplanRequest,
    Subscription,
    User,
    UserPreferences,
    UserProfile,
)
from app.models.base import Base
from app.services.notification_service import NotificationService

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DB, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_session):
    fake_user = TokenUser(uid="uid-notif-test", email="notif@example.com", role="user")

    async def _override_auth():
        return fake_user

    async def _override_premium():
        return fake_user

    def _override_db():
        return db_session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_auth
    app.dependency_overrides[require_premium] = _override_premium

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


# ── Service-level tests ───────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_send_and_list_notification(db_session):
    user = User(firebase_uid="uid-n1", email="n1@example.com")
    db_session.add(user)
    await db_session.flush()

    svc = NotificationService(db_session)
    notif = await svc.send_notification(
        user_id=user.id,
        type="info",
        title="Hello",
        body="Time to focus.",
    )
    await db_session.commit()

    unread = await svc.list_unread(user.id)
    assert len(unread) == 1
    assert unread[0].id == notif.id
    assert unread[0].status == "pending"


@pytest.mark.anyio
async def test_mark_notification_read(db_session):
    user = User(firebase_uid="uid-n2", email="n2@example.com")
    db_session.add(user)
    await db_session.flush()

    svc = NotificationService(db_session)
    notif = await svc.send_notification(user_id=user.id, type="info", title="Hi", body="Hey")
    await db_session.commit()

    result = await svc.mark_read(notif.id, user.id)
    await db_session.commit()
    assert result is True

    unread = await svc.list_unread(user.id)
    assert unread == []


@pytest.mark.anyio
async def test_propose_and_approve_replan(db_session):
    user = User(firebase_uid="uid-n3", email="n3@example.com")
    db_session.add(user)
    await db_session.flush()

    svc = NotificationService(db_session)
    changes = [{"action": "reschedule", "task": "Deep Work", "to": "14:00"}]
    req = await svc.propose_replan(
        user_id=user.id,
        reason="Meeting conflict at 10am",
        proposed_changes=changes,
    )
    await db_session.commit()

    assert req.status == "pending"
    # A notification was also created
    unread = await svc.list_unread(user.id)
    assert any(n.type == "replan_request" for n in unread)

    applied = await svc.approve_replan(request_id=req.id, user_id=user.id)
    await db_session.commit()

    assert applied == changes
    pending = await svc.list_pending_replans(user.id)
    assert pending == []


@pytest.mark.anyio
async def test_reject_replan(db_session):
    user = User(firebase_uid="uid-n4", email="n4@example.com")
    db_session.add(user)
    await db_session.flush()

    svc = NotificationService(db_session)
    req = await svc.propose_replan(
        user_id=user.id,
        reason="Low energy afternoon",
        proposed_changes=[{"action": "move", "task": "Gym", "to": "07:00"}],
    )
    await db_session.commit()

    result = await svc.reject_replan(req.id, user.id)
    assert result is True

    pending = await svc.list_pending_replans(user.id)
    assert pending == []


@pytest.mark.anyio
async def test_double_approve_raises(db_session):
    user = User(firebase_uid="uid-n5", email="n5@example.com")
    db_session.add(user)
    await db_session.flush()

    svc = NotificationService(db_session)
    req = await svc.propose_replan(
        user_id=user.id,
        reason="Back-to-back calls",
        proposed_changes=[{"action": "drop", "task": "Lunch"}],
    )
    await db_session.commit()

    await svc.approve_replan(req.id, user.id)
    await db_session.commit()

    with pytest.raises(ValueError, match="already approved"):
        await svc.approve_replan(req.id, user.id)


# ── API-level tests ───────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_api_send_and_list_notifications(client, db_session):
    user = User(firebase_uid="uid-notif-test", email="notif@example.com")
    db_session.add(user)
    await db_session.commit()

    resp = await client.post("/api/v1/notifications", json={
        "type": "info",
        "title": "Your 3pm block is free",
        "body": "Consider scheduling deep work.",
    })
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"

    list_resp = await client.get("/api/v1/notifications")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


@pytest.mark.anyio
async def test_api_propose_and_approve_replan(client, db_session):
    user = User(firebase_uid="uid-notif-test", email="notif@example.com")
    db_session.add(user)
    await db_session.commit()

    propose_resp = await client.post("/api/v1/notifications/replans", json={
        "reason": "You have a meeting conflict",
        "proposed_changes": [{"action": "move", "task": "Gym", "to": "06:30"}],
    })
    assert propose_resp.status_code == 201
    request_id = propose_resp.json()["id"]

    pending_resp = await client.get("/api/v1/notifications/replans/pending")
    assert pending_resp.status_code == 200
    assert len(pending_resp.json()) == 1

    approve_resp = await client.post(f"/api/v1/notifications/replans/{request_id}/approve")
    assert approve_resp.status_code == 200
    assert approve_resp.json()["applied_changes"][0]["task"] == "Gym"
