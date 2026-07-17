"""TIME-253 — behavioral patterns (running / gym / sitting vs moving / commute) on Insights."""
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 — register tables
from app.core.database import get_db
from app.core.entitlements import require_premium
from app.core.security import TokenUser, get_current_user
from app.main import app
from app.models.base import Base
from app.models.commute import CommuteEvent
from app.models.hourly_activity import HourlyActivity
from app.models.workout_session import WorkoutSession
from app.services.behavioral_patterns_service import BehavioralPatternsService
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
    fake = TokenUser(uid="uid-bp", email="bp@example.com", role="user")
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: fake
    app.dependency_overrides[require_premium] = lambda: fake
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _seed(db):
    user, _ = await UserService(db).get_or_create_user("uid-bp", "bp@example.com")
    now = datetime.now(UTC)
    # 8 morning runs, 5 km / 30 min each
    for i in range(8):
        start = (now - timedelta(days=i * 3 + 1)).replace(hour=7, minute=0, second=0, microsecond=0)
        db.add(WorkoutSession(user_id=user.id, external_id=f"run-{i}", workout_type="running",
                              started_at=start, ended_at=start + timedelta(minutes=30),
                              duration_minutes=30, distance_meters=5000, active_energy_kcal=300))
    # 6 evening strength sessions
    for i in range(6):
        start = (now - timedelta(days=i * 4 + 2)).replace(hour=18, minute=0, second=0, microsecond=0)
        db.add(WorkoutSession(user_id=user.id, external_id=f"gym-{i}", workout_type="strength",
                              started_at=start, ended_at=start + timedelta(minutes=45),
                              duration_minutes=45))
    # 3 days of waking-hour buckets: afternoons sedentary, rest active
    for d in range(3):
        day = (now - timedelta(days=d + 1)).replace(minute=0, second=0, microsecond=0)
        for hour in range(7, 23):
            steps = 40 if 13 <= hour <= 16 else 900
            db.add(HourlyActivity(user_id=user.id, hour_start=day.replace(hour=hour), steps=steps))
    # confirmed commutes (~25 min each)
    for i in range(6):
        s = (now - timedelta(days=i * 2 + 1)).replace(hour=8, minute=0, second=0, microsecond=0)
        db.add(CommuteEvent(user_id=user.id, direction="to_work", detected_start=s,
                            detected_end=s + timedelta(minutes=25), estimated_minutes=25,
                            status="confirmed"))
    await db.commit()
    return user


@pytest.mark.anyio
async def test_service_computes_all_four_patterns(db_session):
    user = await _seed(db_session)
    result = await BehavioralPatternsService(db_session).for_user(user.id, "UTC")
    titles = {p["title"] for p in result["patterns"]}
    assert {"Running", "Gym", "Sitting vs. moving", "Commute"} <= titles
    running = next(p for p in result["patterns"] if p["title"] == "Running")
    assert "miles/week" in running["detail"] and "mornings" in running["detail"]
    sitting = next(p for p in result["patterns"] if p["title"] == "Sitting vs. moving")
    assert "%" in sitting["detail"]
    commute = next(p for p in result["patterns"] if p["title"] == "Commute")
    assert "commute" in commute["detail"]
    assert result["based_on_days"] == 28


@pytest.mark.anyio
async def test_no_data_returns_empty(db_session):
    await UserService(db_session).get_or_create_user("uid-bp", "bp@example.com")
    result = await BehavioralPatternsService(db_session).for_user(
        (await UserService(db_session).get_or_create_user("uid-bp", "bp@example.com"))[0].id, "UTC"
    )
    assert result["patterns"] == []


@pytest.mark.anyio
async def test_patterns_endpoint_premium(client, db_session):
    await _seed(db_session)
    resp = await client.get("/api/v1/insights/patterns")
    assert resp.status_code == 200
    body = resp.json()
    assert body["based_on_days"] == 28
    assert any(p["title"] == "Running" for p in body["patterns"])
    assert all({"category", "icon", "title", "detail"} <= p.keys() for p in body["patterns"])
