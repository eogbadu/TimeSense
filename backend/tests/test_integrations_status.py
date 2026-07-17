"""TIME-240 — GET /integrations/status reflects which providers the user has connected, so the
clients can show Disconnect instead of Connect. Email also gains a DELETE /email/disconnect route."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.core.entitlements import require_premium
from app.core.security import TokenUser, get_current_user
from app.main import app
from app.models import (  # noqa: F401 — register tables
    AssistantPersonality,
    CalendarIntegration,
    ConsentRecord,
    OnboardingState,
    Subscription,
    User,
    UserPreferences,
    UserProfile,
)
from app.models.base import Base
from app.repositories.calendar_repository import CalendarIntegrationRepository
from app.repositories.email_repository import EmailIntegrationRepository
from app.services.user_service import UserService

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def anyio_backend():
    return "asyncio"


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
    fake_user = TokenUser(uid="uid-status-test", email="status@example.com", role="user")
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[require_premium] = lambda: fake_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_status_all_disconnected(client):
    resp = await client.get("/api/v1/integrations/status")
    assert resp.status_code == 200
    assert resp.json() == {
        "google": False, "microsoft": False, "gmail": False, "slack": False, "notion": False,
    }


@pytest.mark.anyio
async def test_status_reflects_connected_calendar_and_email(client, db_session):
    user, _ = await UserService(db_session).get_or_create_user("uid-status-test", "status@example.com")
    await CalendarIntegrationRepository(db_session).upsert(
        user.id, "google", "atok", "rtok", None
    )
    await EmailIntegrationRepository(db_session).upsert(
        user.id, "atok", "rtok", None, provider="gmail"
    )
    await db_session.commit()

    resp = await client.get("/api/v1/integrations/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["google"] is True
    assert body["gmail"] is True
    assert body["microsoft"] is False and body["slack"] is False and body["notion"] is False


@pytest.mark.anyio
async def test_email_disconnect(client, db_session):
    user, _ = await UserService(db_session).get_or_create_user("uid-status-test", "status@example.com")
    await EmailIntegrationRepository(db_session).upsert(
        user.id, "atok", "rtok", None, provider="gmail"
    )
    await db_session.commit()

    resp = await client.delete("/api/v1/email/disconnect")
    assert resp.status_code == 204

    status = await client.get("/api/v1/integrations/status")
    assert status.json()["gmail"] is False

    # Idempotent-ish: a second disconnect reports 404 (nothing active).
    again = await client.delete("/api/v1/email/disconnect")
    assert again.status_code == 404
