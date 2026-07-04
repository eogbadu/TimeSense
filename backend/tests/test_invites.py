"""Tests for waitlist and invite code system."""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.core.security import TokenUser, get_current_user
from app.main import app
from app.models import (  # noqa: F401
    AssistantPersonality,
    CalendarIntegration,
    ConsentRecord,
    InviteCode,
    Notification,
    OnboardingState,
    PendingCalendarAction,
    ReplanRequest,
    Subscription,
    User,
    UserPreferences,
    UserProfile,
    WaitlistEntry,
)
from app.models.base import Base
from app.services.invite_service import InviteService

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
async def admin_user(db_session):
    user = User(firebase_uid="uid-admin", email="admin@example.com", role="admin")
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def client(db_session, admin_user):
    fake_user = TokenUser(uid="uid-admin", email="admin@example.com", role="admin")

    async def _override_auth():
        return fake_user

    def _override_db():
        return db_session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_auth

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_join_waitlist_idempotent(db_session):
    svc = InviteService(db_session)
    entry1 = await svc.join_waitlist("user@example.com")
    await db_session.commit()
    entry2 = await svc.join_waitlist("user@example.com")
    assert entry1.id == entry2.id
    assert entry1.position == 1


@pytest.mark.anyio
async def test_waitlist_position_ordering(db_session):
    svc = InviteService(db_session)
    await svc.join_waitlist("first@example.com")
    await svc.join_waitlist("second@example.com")
    await db_session.commit()
    assert await svc.get_waitlist_position("first@example.com") == 1
    assert await svc.get_waitlist_position("second@example.com") == 2


@pytest.mark.anyio
async def test_create_and_validate_invite_code(db_session, admin_user):
    svc = InviteService(db_session)
    code = await svc.create_invite_code(created_by_id=admin_user.id, max_uses=5)
    await db_session.commit()
    assert await svc.validate_invite_code(code.code) is True
    assert await svc.validate_invite_code("NOTAREALCODE") is False


@pytest.mark.anyio
async def test_consume_invite_code(db_session, admin_user):
    svc = InviteService(db_session)
    code = await svc.create_invite_code(created_by_id=admin_user.id, max_uses=1)
    await db_session.commit()
    consumed = await svc.consume_invite_code(code.code)
    await db_session.commit()
    assert consumed is not None and consumed.uses == 1
    assert await svc.consume_invite_code(code.code) is None


@pytest.mark.anyio
async def test_disable_invite_code(db_session, admin_user):
    svc = InviteService(db_session)
    code = await svc.create_invite_code(created_by_id=admin_user.id)
    await db_session.commit()
    await svc.disable_invite_code(code.code)
    await db_session.commit()
    assert await svc.validate_invite_code(code.code) is False


@pytest.mark.anyio
async def test_invite_from_waitlist(db_session, admin_user):
    svc = InviteService(db_session)
    entry = await svc.join_waitlist("waitlisted@example.com")
    await db_session.commit()
    invite_code = await svc.invite_from_waitlist(entry_id=entry.id, admin_user_id=admin_user.id)
    await db_session.commit()
    assert invite_code is not None and invite_code.max_uses == 1


@pytest.mark.anyio
async def test_api_join_waitlist(client):
    resp = await client.post("/api/v1/invites/waitlist", json={"email": "signup@example.com"})
    assert resp.status_code == 201
    assert resp.json()["status"] == "waiting"
    assert resp.json()["position"] == 1


@pytest.mark.anyio
async def test_api_create_and_validate_code(client):
    create_resp = await client.post("/api/v1/invites/codes", json={"max_uses": 3})
    assert create_resp.status_code == 201
    code = create_resp.json()["code"]
    assert (await client.post("/api/v1/invites/validate", json={"code": code})).json()["valid"] is True
    assert (await client.post("/api/v1/invites/validate", json={"code": "BADCODE"})).json()["valid"] is False
