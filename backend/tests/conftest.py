import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app

# In-memory SQLite for unit tests — no Postgres required for running the test suite.
# Integration tests that need real Postgres behaviour use a separate test database
# and are marked with @pytest.mark.integration.
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    # Shared in-process limiters accumulate state across tests (same auth token) — reset each test.
    from app.core.rate_limit import _reset_all

    _reset_all()
    yield


@pytest.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # SQLite doesn't enforce foreign keys (or ON DELETE CASCADE) unless asked per-connection.
    # Turn it on so cascade behaviour (e.g. account deletion, TIME-055) is exercised like Postgres.
    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fk(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


async def expire_intro_trial(db_session, uid: str, email: str):
    """Age a user past the free intro-trial window so Premium gates apply again (returns the user).

    Everyone is Premium for their first `intro_trial_days` (TIME-178); tests that exercise the
    non-premium 403 path must first push the account beyond that window.
    """
    from datetime import UTC, datetime, timedelta

    from app.core.config import settings
    from app.services.user_service import UserService

    user, _ = await UserService(db_session).get_or_create_user(uid, email)
    user.created_at = datetime.now(UTC) - timedelta(days=settings.intro_trial_days + 1)
    await db_session.flush()
    return user


@pytest.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
