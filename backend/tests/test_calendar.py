"""
Tests for calendar service approval flow.
No real HTTP calls — GoogleCalendarProvider is patched at the service level.
"""
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.core.entitlements import require_premium
from app.core.security import get_current_user
from app.integrations.calendar_base import CalendarEvent, CalendarEventCreate
from app.main import app
from app.models import (  # noqa: F401 — register all tables
    AssistantPersonality,
    CalendarIntegration,
    ConsentRecord,
    OnboardingState,
    PendingCalendarAction,
    Subscription,
    User,
    UserPreferences,
    UserProfile,
)
from app.models.base import Base
from app.services.calendar_service import CalendarService

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
    from app.core.security import TokenUser

    def _override_db():
        return db_session

    fake_user = TokenUser(uid="uid-cal-test", email="cal@example.com", role="user")

    async def _override_auth():
        return fake_user

    async def _override_premium():
        return fake_user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_auth
    app.dependency_overrides[require_premium] = _override_premium

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


# ── Service-level tests ───────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_connect_and_get_integration(db_session):
    user = User(firebase_uid="uid-c1", email="c1@example.com")
    db_session.add(user)
    await db_session.flush()

    svc = CalendarService(db_session)
    await svc.connect(
        user_id=user.id,
        provider="google",
        access_token="tok_abc",
        refresh_token="ref_abc",
    )
    await db_session.commit()

    fetched = await svc.get_integration(user.id, "google")
    assert fetched is not None
    assert fetched.access_token == "tok_abc"
    assert fetched.is_active is True


@pytest.mark.anyio
async def test_disconnect(db_session):
    user = User(firebase_uid="uid-c2", email="c2@example.com")
    db_session.add(user)
    await db_session.flush()

    svc = CalendarService(db_session)
    await svc.connect(user_id=user.id, provider="google", access_token="tok")
    await db_session.commit()

    result = await svc.disconnect(user.id, "google")
    await db_session.commit()
    assert result is True

    fetched = await svc.get_integration(user.id, "google")
    assert fetched is None


@pytest.mark.anyio
async def test_request_and_approve_action(db_session):
    user = User(firebase_uid="uid-c3", email="c3@example.com")
    db_session.add(user)
    await db_session.flush()

    svc = CalendarService(db_session)
    await svc.connect(user_id=user.id, provider="google", access_token="tok_google")
    await db_session.commit()

    event = CalendarEventCreate(
        title="Team Sync",
        start=datetime(2026, 7, 10, 9, 0, tzinfo=UTC),
        end=datetime(2026, 7, 10, 9, 30, tzinfo=UTC),
    )
    action = await svc.request_event_creation(user_id=user.id, provider="google", event=event)
    await db_session.commit()

    assert action.status == "pending"
    payload = json.loads(action.event_payload)
    assert payload["title"] == "Team Sync"

    mock_event = CalendarEvent(
        event_id="gcal-evt-001",
        title="Team Sync",
        start=event.start,
        end=event.end,
        calendar_id="primary",
        provider="google",
    )
    with patch(
        "app.services.calendar_service.GoogleCalendarProvider.create_event",
        new=AsyncMock(return_value=mock_event),
    ):
        created = await svc.approve_action(action_id=action.id, user_id=user.id)

    await db_session.commit()
    assert created.event_id == "gcal-evt-001"

    pending = await svc.list_pending_actions(user.id)
    assert pending == []


@pytest.mark.anyio
async def test_reject_action(db_session):
    user = User(firebase_uid="uid-c4", email="c4@example.com")
    db_session.add(user)
    await db_session.flush()

    svc = CalendarService(db_session)
    event = CalendarEventCreate(
        title="Cancel Me",
        start=datetime(2026, 7, 11, 10, 0, tzinfo=UTC),
        end=datetime(2026, 7, 11, 11, 0, tzinfo=UTC),
    )
    action = await svc.request_event_creation(user_id=user.id, provider="google", event=event)
    await db_session.commit()

    result = await svc.reject_action(action_id=action.id, user_id=user.id)
    assert result is True

    pending = await svc.list_pending_actions(user.id)
    assert pending == []


@pytest.mark.anyio
async def test_approve_already_approved_raises(db_session):
    user = User(firebase_uid="uid-c5", email="c5@example.com")
    db_session.add(user)
    await db_session.flush()

    svc = CalendarService(db_session)
    await svc.connect(user_id=user.id, provider="google", access_token="tok")
    event = CalendarEventCreate(
        title="Double Approve",
        start=datetime(2026, 7, 12, 9, 0, tzinfo=UTC),
        end=datetime(2026, 7, 12, 10, 0, tzinfo=UTC),
    )
    action = await svc.request_event_creation(user_id=user.id, provider="google", event=event)
    await db_session.commit()

    mock_event = CalendarEvent(
        event_id="gcal-evt-002",
        title="Double Approve",
        start=event.start,
        end=event.end,
        calendar_id="primary",
        provider="google",
    )
    with patch(
        "app.services.calendar_service.GoogleCalendarProvider.create_event",
        new=AsyncMock(return_value=mock_event),
    ):
        await svc.approve_action(action_id=action.id, user_id=user.id)
    await db_session.commit()

    with pytest.raises(ValueError, match="already approved"):
        await svc.approve_action(action_id=action.id, user_id=user.id)


# ── API-level tests ───────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_api_connect_calendar(client, db_session):
    # Seed user
    user = User(firebase_uid="uid-cal-test", email="cal@example.com")
    db_session.add(user)
    await db_session.commit()

    resp = await client.post("/api/v1/calendar/connect", json={
        "provider": "google",
        "access_token": "tok_api",
        "calendar_id": "primary",
    })
    assert resp.status_code == 201
    assert resp.json()["provider"] == "google"


@pytest.mark.anyio
async def test_api_request_and_list_pending(client, db_session):
    user = User(firebase_uid="uid-cal-test", email="cal@example.com")
    db_session.add(user)
    await db_session.commit()

    resp = await client.post("/api/v1/calendar/actions/request?provider=google", json={
        "title": "Doctor Appointment",
        "start": "2026-07-15T10:00:00",
        "end": "2026-07-15T11:00:00",
    })
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"

    list_resp = await client.get("/api/v1/calendar/actions/pending")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["status"] == "pending"
