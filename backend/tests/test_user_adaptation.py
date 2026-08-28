"""TIME-292 — the adaptation profile.

The point of the table is that the engine can afford to consult it. The point of these tests is the
two rules that make it safe to consult:

  * null, not zero, below a sample floor — "no evidence" and "evidence of nothing" are different
    claims, and conflating them scores a brand-new user on noise;
  * bucketing happens in the USER'S timezone, not UTC, or the hour-of-day profile is meaningless
    for anyone who isn't near UTC and silently re-buckets when they travel.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.task import Task
from app.repositories.user_adaptation_repository import UserAdaptationRepository
from app.repositories.user_repository import UserRepository
from app.services.user_adaptation_service import (
    MIN_SAMPLES_PER_BUCKET,
    UserAdaptationService,
    _median,
)
from app.services.user_service import UserService

NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


async def _user(db, uid="uid-adapt", tz="UTC"):
    user, _ = await UserService(db).get_or_create_user(uid, f"{uid}@example.com")
    await UserRepository(db).update_profile(user.id, timezone=tz)
    return user


def _task(user_id, *, hour, done, days_ago=1, tz_offset=0):
    when = (NOW - timedelta(days=days_ago)).replace(hour=hour, minute=0)
    return Task(
        user_id=user_id, title="Write the report",
        status="done" if done else "pending", priority=3,
        scheduled_start=when, scheduled_end=when + timedelta(minutes=30),
        created_at=when,
    )


@pytest.mark.anyio
async def test_a_new_user_gets_an_all_null_profile(db_session):
    """The most important case. A user with no history must produce no claims at all, so every
    consumer stays neutral instead of scoring them on nothing."""
    user = await _user(db_session, "uid-adapt-new")
    profile = await UserAdaptationService(db_session).rebuild(user.id, now=NOW)

    assert profile.completion_by_hour is None
    assert profile.completion_by_weekday is None
    assert profile.acceptance_by_category is None
    assert profile.acceptance_by_action_type is None
    assert profile.estimate_ratio_by_type is None
    assert profile.completions_by_energy is None
    assert profile.energy_bias is None
    assert profile.typical_wake_minute is None
    assert profile.typical_first_task_minute is None


@pytest.mark.anyio
async def test_a_bucket_below_the_sample_floor_is_absent_not_zero(db_session):
    """One or two data points is not a habit. Reporting 0.0 would read as "never completes at 9am",
    which is a much stronger claim than the evidence supports."""
    user = await _user(db_session, "uid-adapt-thin")
    for _ in range(MIN_SAMPLES_PER_BUCKET - 1):
        db_session.add(_task(user.id, hour=9, done=False))
    await db_session.flush()

    profile = await UserAdaptationService(db_session).rebuild(user.id, now=NOW)
    hours = profile.completion_by_hour or {}
    assert "9" not in hours


@pytest.mark.anyio
async def test_completion_rate_appears_once_there_is_enough_evidence(db_session):
    user = await _user(db_session, "uid-adapt-rate")
    for i in range(4):
        db_session.add(_task(user.id, hour=9, done=True, days_ago=i + 1))
    for i in range(4):
        db_session.add(_task(user.id, hour=22, done=False, days_ago=i + 1))
    await db_session.flush()

    profile = await UserAdaptationService(db_session).rebuild(user.id, now=NOW)
    hours = profile.completion_by_hour
    assert hours is not None
    assert hours["9"] == 1.0
    assert hours["22"] == 0.0
    assert hours["9"] > hours["22"], "the profile must be able to tell these apart"


@pytest.mark.anyio
async def test_hours_are_bucketed_in_the_users_timezone_not_utc(db_session):
    """A UTC-bucketed hour profile is wrong for everyone outside UTC, and silently re-buckets when
    the user travels (TIME-283 fixed the same class of bug in the read paths)."""
    user = await _user(db_session, "uid-adapt-tokyo", tz="Asia/Tokyo")
    # 00:00 UTC is 09:00 in Tokyo.
    for i in range(4):
        db_session.add(_task(user.id, hour=0, done=True, days_ago=i + 1))
    await db_session.flush()

    profile = await UserAdaptationService(db_session).rebuild(user.id, now=NOW)
    assert profile.timezone == "Asia/Tokyo"
    assert "9" in (profile.completion_by_hour or {}), profile.completion_by_hour
    assert "0" not in (profile.completion_by_hour or {})


@pytest.mark.anyio
async def test_estimate_accuracy_is_reported_per_task_type(db_session):
    """actual / predicted, so the assistant can see where it is systematically wrong."""
    from app.services.task_duration_service import TaskDurationEstimator

    user = await _user(db_session, "uid-adapt-est")
    est = TaskDurationEstimator(db_session)
    for _ in range(4):
        await est.record_actual(user.id, "Buy groceries", 60, estimated_minutes=30)
    await db_session.flush()

    profile = await UserAdaptationService(db_session).rebuild(user.id, now=NOW)
    ratios = profile.estimate_ratio_by_type
    assert ratios is not None
    assert ratios["shop_groceries"] == 2.0, "60 actual vs 30 predicted is a 2x under-estimate"


@pytest.mark.anyio
async def test_energy_bias_is_the_signed_gap_between_reported_and_inferred(db_session):
    """Negative means we consistently claim more capacity than the user reports having."""
    from app.repositories.energy_checkin_repository import EnergyCheckInRepository

    user = await _user(db_session, "uid-adapt-energy")
    repo = EnergyCheckInRepository(db_session)
    for i in range(6):
        await repo.create(user.id, reported="low", inferred="high",
                          reported_at=NOW - timedelta(days=i + 1))
    await db_session.flush()

    profile = await UserAdaptationService(db_session).rebuild(user.id, now=NOW)
    assert profile.energy_bias == -2.0, "low(0) - high(2) == -2 every time"


@pytest.mark.anyio
async def test_energy_bias_stays_absent_below_the_floor(db_session):
    from app.repositories.energy_checkin_repository import EnergyCheckInRepository

    user = await _user(db_session, "uid-adapt-energy-thin")
    await EnergyCheckInRepository(db_session).create(
        user.id, reported="low", inferred="high", reported_at=NOW - timedelta(days=1)
    )
    await db_session.flush()
    profile = await UserAdaptationService(db_session).rebuild(user.id, now=NOW)
    assert profile.energy_bias is None


@pytest.mark.anyio
async def test_rebuild_is_idempotent(db_session):
    """The nightly job must be safely re-runnable — a retry can't be allowed to duplicate rows."""
    from sqlalchemy import func, select

    from app.models.user_adaptation_profile import UserAdaptationProfile

    user = await _user(db_session, "uid-adapt-idem")
    svc = UserAdaptationService(db_session)
    await svc.rebuild(user.id, now=NOW)
    await svc.rebuild(user.id, now=NOW + timedelta(hours=1))

    count = (await db_session.execute(
        select(func.count()).select_from(UserAdaptationProfile)
        .where(UserAdaptationProfile.user_id == user.id)
    )).scalar_one()
    assert count == 1


@pytest.mark.anyio
async def test_the_profile_is_a_single_indexed_read(db_session):
    """The engine consults this on every recommendation, so reading it must be trivial."""
    user = await _user(db_session, "uid-adapt-read")
    await UserAdaptationService(db_session).rebuild(user.id, now=NOW)
    row = await UserAdaptationRepository(db_session).get(user.id)
    assert row is not None
    assert row.user_id == user.id


def test_typical_times_use_a_median_so_one_odd_day_does_not_move_them():
    """A single 3am night must not redefine someone's typical wake time."""
    normal = [420, 425, 430, 435, 440]
    with_outlier = normal + [180]
    assert _median(normal) == 430
    assert abs(_median(with_outlier) - 430) <= 5
