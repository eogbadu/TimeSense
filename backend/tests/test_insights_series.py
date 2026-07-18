"""
Service-layer tests for the Insights chart series (TIME-273): daily activity, weekly running
mileage, and the average-steps-by-hour profile. SQLite in-memory, matching test_insights.py.
"""
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.daily_activity import DailyActivity
from app.models.hourly_activity import HourlyActivity
from app.models.workout_session import WorkoutSession
from app.services.insights_series_service import InsightsSeriesService
from app.services.user_service import UserService

TEST_DB = "sqlite+aiosqlite:///:memory:"
_MILE = 1609.344


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


async def _user(db_session):
    user, _ = await UserService(db_session).get_or_create_user("u1", "u1@example.com")
    return user


async def test_daily_activity_returns_points_in_window(db_session):
    user = await _user(db_session)
    today = datetime.now(timezone.utc).date()
    db_session.add_all([
        DailyActivity(user_id=user.id, day=today, steps=8000, exercise_minutes=30),
        DailyActivity(user_id=user.id, day=today - timedelta(days=2), steps=4000, exercise_minutes=None),
        DailyActivity(user_id=user.id, day=today - timedelta(days=40), steps=1000, exercise_minutes=0),
    ])
    await db_session.flush()

    points = await InsightsSeriesService(db_session).daily_activity(user.id, days=30)

    assert [p["day"] for p in points] == [today - timedelta(days=2), today]  # oldest first, 40d excluded
    assert points[-1] == {"day": today, "steps": 8000, "exercise_minutes": 30}
    assert points[0]["exercise_minutes"] == 0  # None coerced to 0


async def test_weekly_workouts_buckets_running_miles(db_session):
    user = await _user(db_session)
    now = datetime.now(timezone.utc)

    def _run(days_ago: int, meters: float) -> WorkoutSession:
        started = now - timedelta(days=days_ago)
        return WorkoutSession(
            user_id=user.id, external_id=f"w{days_ago}", workout_type="running",
            started_at=started, ended_at=started + timedelta(minutes=30),
            duration_minutes=30, distance_meters=meters,
        )

    db_session.add_all([_run(1, 5 * _MILE), _run(2, 3 * _MILE)])  # two runs this week
    await db_session.flush()

    points = await InsightsSeriesService(db_session).weekly_workouts(user.id, weeks=8)

    assert len(points) == 8  # continuous timeline, zero-filled
    latest = points[-1]
    assert latest["running_count"] == 2
    assert latest["total_count"] == 2
    assert latest["running_miles"] == pytest.approx(8.0, abs=0.01)
    assert points[0] == {"week_start": points[0]["week_start"], "running_miles": 0.0,
                         "running_count": 0, "total_count": 0}


async def test_weekly_workouts_counts_non_running_in_total_only(db_session):
    user = await _user(db_session)
    now = datetime.now(timezone.utc)
    db_session.add(WorkoutSession(
        user_id=user.id, external_id="g1", workout_type="strength",
        started_at=now - timedelta(days=1), ended_at=now, duration_minutes=45,
        distance_meters=None,
    ))
    await db_session.flush()

    latest = (await InsightsSeriesService(db_session).weekly_workouts(user.id, weeks=4))[-1]
    assert latest["total_count"] == 1
    assert latest["running_count"] == 0
    assert latest["running_miles"] == 0.0


async def test_hourly_steps_averages_over_active_days(db_session):
    user = await _user(db_session)
    now = datetime.now(timezone.utc)
    # Two different days, same hour bucket (09:00 UTC) → averaged, not summed.
    for days_ago in (1, 2):
        base = (now - timedelta(days=days_ago)).replace(hour=9, minute=0, second=0, microsecond=0)
        db_session.add(HourlyActivity(user_id=user.id, hour_start=base, steps=1000))
    await db_session.flush()

    points = await InsightsSeriesService(db_session).hourly_steps(user.id, days=7, user_timezone="UTC")

    assert len(points) == 24
    by_hour = {p["hour"]: p["avg_steps"] for p in points}
    assert by_hour[9] == 1000   # 2000 total / 2 active days
    assert by_hour[3] == 0


async def test_series_empty_when_no_data(db_session):
    user = await _user(db_session)
    svc = InsightsSeriesService(db_session)
    assert await svc.daily_activity(user.id, days=30) == []
    workouts = await svc.weekly_workouts(user.id, weeks=4)
    assert len(workouts) == 4 and all(p["total_count"] == 0 for p in workouts)
    hourly = await svc.hourly_steps(user.id, days=7)
    assert len(hourly) == 24 and all(p["avg_steps"] == 0 for p in hourly)
