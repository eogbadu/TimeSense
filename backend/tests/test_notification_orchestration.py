"""
Tests for NotificationService's check-in/check-out/learning-prompt orchestration (TIME-043).
Tested at the service layer against db_session, matching test_notifications.py's existing
pattern for flows that aren't triggered by an HTTP request.
"""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models import (  # noqa: F401
    AssistantPersonality,
    CalendarIntegration,
    CommuteEvent,
    ConsentRecord,
    InviteCode,
    MealEvent,
    Notification,
    NotificationEvent,
    OnboardingState,
    PendingCalendarAction,
    RecommendationFeedback,
    ReferralCode,
    ReferralConversion,
    ReplanRequest,
    RoutineAssumption,
    SleepWakeEvent,
    Subscription,
    Task,
    User,
    UserPreferences,
    UserProfile,
    WaitlistEntry,
)
from app.models.base import Base
from app.repositories.routine_repository import RoutineAssumptionRepository
from app.repositories.user_repository import UserRepository
from app.services.notification_service import LEARNING_PERIOD_DAYS, NotificationService
from app.services.user_service import UserService

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


async def _make_user(db_session, uid: str, mode: str, onboarding_complete: bool = True):
    user, _ = await UserService(db_session).get_or_create_user(uid, f"{uid}@example.com")
    await UserRepository(db_session).update_preferences(user.id, notification_mode=mode)
    if onboarding_complete:
        user.onboarding_complete = True
    await db_session.flush()
    return user


@pytest.mark.anyio
async def test_gentle_mode_skips_morning_checkin_but_sends_evening(db_session):
    user = await _make_user(db_session, "uid-gentle", "gentle")
    svc = NotificationService(db_session)

    morning = await svc.maybe_send_morning_checkin(user.id)
    evening = await svc.maybe_send_evening_checkout(user.id)

    assert morning is None
    assert evening is not None


@pytest.mark.anyio
async def test_balanced_mode_sends_both_checkins_no_learning_prompt(db_session):
    user = await _make_user(db_session, "uid-balanced", "balanced")
    svc = NotificationService(db_session)

    morning = await svc.maybe_send_morning_checkin(user.id)
    evening = await svc.maybe_send_evening_checkout(user.id)
    learning = await svc.maybe_send_routine_learning_prompt(user.id)

    assert morning is not None
    assert evening is not None
    assert learning is None


@pytest.mark.anyio
async def test_active_coach_sends_learning_prompt_for_default_routine(db_session):
    user = await _make_user(db_session, "uid-coach", "active_coach")
    await RoutineAssumptionRepository(db_session).get_or_seed_defaults(user.id)
    svc = NotificationService(db_session)

    morning = await svc.maybe_send_morning_checkin(user.id)
    evening = await svc.maybe_send_evening_checkout(user.id)
    learning = await svc.maybe_send_routine_learning_prompt(user.id)

    assert morning is not None
    assert evening is not None
    assert learning is not None
    assert "sleep" in learning.body.lower()


@pytest.mark.anyio
async def test_learning_prompt_skipped_once_routine_is_customized(db_session):
    user = await _make_user(db_session, "uid-customized", "active_coach")
    routine_repo = RoutineAssumptionRepository(db_session)
    await routine_repo.get_or_seed_defaults(user.id)
    await routine_repo.update_one(user.id, "sleep", start_minute=22 * 60, end_minute=6 * 60)

    svc = NotificationService(db_session)
    learning = await svc.maybe_send_routine_learning_prompt(user.id)

    assert learning is None


@pytest.mark.anyio
async def test_learning_prompt_skipped_outside_learning_window(db_session):
    user = await _make_user(db_session, "uid-old-account", "active_coach")
    await RoutineAssumptionRepository(db_session).get_or_seed_defaults(user.id)
    user.created_at = datetime.now(UTC) - timedelta(days=LEARNING_PERIOD_DAYS + 1)
    await db_session.flush()

    svc = NotificationService(db_session)
    learning = await svc.maybe_send_routine_learning_prompt(user.id)

    assert learning is None


@pytest.mark.anyio
async def test_learning_prompt_skipped_before_onboarding_complete(db_session):
    user = await _make_user(db_session, "uid-onboarding", "active_coach", onboarding_complete=False)
    await RoutineAssumptionRepository(db_session).get_or_seed_defaults(user.id)

    svc = NotificationService(db_session)
    learning = await svc.maybe_send_routine_learning_prompt(user.id)

    assert learning is None


@pytest.mark.anyio
async def test_checkins_are_once_per_day(db_session):
    user = await _make_user(db_session, "uid-dedup", "balanced")
    svc = NotificationService(db_session)

    first = await svc.maybe_send_morning_checkin(user.id)
    second = await svc.maybe_send_morning_checkin(user.id)

    assert first is not None
    assert second is None


@pytest.mark.anyio
async def test_checkins_are_per_user(db_session):
    user_a = await _make_user(db_session, "uid-a", "gentle")
    user_b = await _make_user(db_session, "uid-b", "gentle")
    svc = NotificationService(db_session)

    a_evening = await svc.maybe_send_evening_checkout(user_a.id)
    b_evening = await svc.maybe_send_evening_checkout(user_b.id)

    assert a_evening is not None
    assert b_evening is not None
    assert a_evening.id != b_evening.id


@pytest.mark.anyio
async def test_unknown_notification_mode_sends_nothing(db_session):
    # A user with no preferences row (edge case) should be treated as opted out, not crash.
    user, _ = await UserService(db_session).get_or_create_user("uid-no-prefs", "no-prefs@example.com")
    user.preferences = None
    await db_session.flush()

    svc = NotificationService(db_session)
    morning = await svc.maybe_send_morning_checkin(user.id)

    assert morning is None
