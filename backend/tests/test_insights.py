"""
Tests for weekly insight generation (TIME-046).

Aggregation-math tests run at the service layer (own db_session, matching
test_notification_orchestration.py's pattern for non-HTTP-triggered flows).
API-layer tests (premium gate, endpoint wiring, isolation) use the shared
client/db_session fixtures from conftest.py, matching test_commutes.py etc.
"""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import TokenUser
from app.llm.gateway import LLMGateway, LLMResponse, _NoOpProvider, get_llm_gateway, set_llm_gateway
from app.models.base import Base
from app.models.commute import CommuteEvent
from app.models.meal import MealEvent
from app.models.notification import ReplanRequest
from app.models.recommendation_feedback import RecommendationFeedback
from app.models.sleep_wake import SleepWakeEvent
from app.models.subscription import Subscription
from app.repositories.task_repository import TaskRepository
from app.services.insights_service import InsightsService, most_recently_completed_week
from app.services.user_service import UserService

TEST_DB = "sqlite+aiosqlite:///:memory:"

# A fixed, fully-elapsed Monday-Sunday week used across every service-level test.
WEEK_START = date(2026, 6, 22)  # Monday
WEEK_END = date(2026, 6, 28)  # Sunday


def _in_week(day_offset: int, hour: int = 12) -> datetime:
    return datetime(WEEK_START.year, WEEK_START.month, WEEK_START.day, hour, tzinfo=timezone.utc) \
        + timedelta(days=day_offset)


# ── Service-layer tests ───────────────────────────────────────────────────────

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


@pytest.fixture(autouse=True)
def reset_gateway():
    import app.llm.gateway as _gw_mod
    original = _gw_mod._gateway
    set_llm_gateway(LLMGateway(provider=_NoOpProvider()))
    yield
    _gw_mod._gateway = original


async def _make_user(db_session, uid: str):
    user, _ = await UserService(db_session).get_or_create_user(uid, f"{uid}@example.com")
    return user


async def _add_task(db_session, user_id, created_at: datetime, status: str = "pending", updated_at: datetime | None = None):
    task = await TaskRepository(db_session).create(user_id=user_id, title="Task", status=status)
    task.created_at = created_at
    if updated_at is not None:
        task.updated_at = updated_at
    await db_session.flush()
    return task


async def _add_meal(db_session, user_id, meal_type: str, status: str, occurred_at: datetime):
    event = MealEvent(user_id=user_id, meal_type=meal_type, status=status, occurred_at=occurred_at)
    db_session.add(event)
    await db_session.flush()
    return event


async def _add_sleep_event(db_session, user_id, wake_time: datetime, replanned: bool = False):
    replan_request_id = None
    if replanned:
        req = ReplanRequest(
            user_id=user_id,
            reason="late wake",
            proposed_changes="[]",
            expires_at=wake_time + timedelta(hours=12),
        )
        db_session.add(req)
        await db_session.flush()
        replan_request_id = req.id
    event = SleepWakeEvent(user_id=user_id, wake_time=wake_time, source="manual", replan_request_id=replan_request_id)
    db_session.add(event)
    await db_session.flush()
    return event


async def _add_commute(db_session, user_id, detected_start: datetime, status: str = "confirmed"):
    event = CommuteEvent(
        user_id=user_id,
        direction="to_work",
        detected_start=detected_start,
        detected_end=detected_start + timedelta(minutes=30),
        estimated_minutes=30,
        status=status,
    )
    db_session.add(event)
    await db_session.flush()
    return event


async def _add_feedback(db_session, user_id, task_id, signal: str, created_at: datetime):
    fb = RecommendationFeedback(user_id=user_id, task_id=task_id, signal=signal)
    db_session.add(fb)
    await db_session.flush()
    fb.created_at = created_at
    await db_session.flush()
    return fb


@pytest.mark.anyio
async def test_completion_rate_and_task_counts(db_session):
    user = await _make_user(db_session, "uid-ins-1")
    await _add_task(db_session, user.id, created_at=_in_week(0), status="done", updated_at=_in_week(1))
    await _add_task(db_session, user.id, created_at=_in_week(2), status="done", updated_at=_in_week(2))
    await _add_task(db_session, user.id, created_at=_in_week(3), status="pending")

    svc = InsightsService(db_session, get_llm_gateway())
    insight = await svc.get_or_generate_for_week(user.id, WEEK_START, WEEK_END)

    assert insight.tasks_total == 3
    assert insight.tasks_completed == 2
    assert insight.completion_rate == pytest.approx(2 / 3)


@pytest.mark.anyio
async def test_no_tasks_created_gives_none_completion_rate(db_session):
    user = await _make_user(db_session, "uid-ins-2")
    svc = InsightsService(db_session, get_llm_gateway())
    insight = await svc.get_or_generate_for_week(user.id, WEEK_START, WEEK_END)

    assert insight.tasks_total == 0
    assert insight.completion_rate is None


@pytest.mark.anyio
async def test_most_skipped_meal_picks_highest_count(db_session):
    user = await _make_user(db_session, "uid-ins-3")
    await _add_meal(db_session, user.id, "lunch", "skipped", _in_week(0))
    await _add_meal(db_session, user.id, "lunch", "skipped", _in_week(1))
    await _add_meal(db_session, user.id, "dinner", "skipped", _in_week(2))

    svc = InsightsService(db_session, get_llm_gateway())
    insight = await svc.get_or_generate_for_week(user.id, WEEK_START, WEEK_END)

    assert insight.most_skipped_meal == "lunch"


@pytest.mark.anyio
async def test_most_skipped_meal_ties_break_alphabetically(db_session):
    user = await _make_user(db_session, "uid-ins-4")
    await _add_meal(db_session, user.id, "lunch", "skipped", _in_week(0))
    await _add_meal(db_session, user.id, "breakfast", "skipped", _in_week(1))

    svc = InsightsService(db_session, get_llm_gateway())
    insight = await svc.get_or_generate_for_week(user.id, WEEK_START, WEEK_END)

    assert insight.most_skipped_meal == "breakfast"


@pytest.mark.anyio
async def test_no_skipped_meals_returns_none(db_session):
    user = await _make_user(db_session, "uid-ins-5")
    await _add_meal(db_session, user.id, "lunch", "eaten", _in_week(0))

    svc = InsightsService(db_session, get_llm_gateway())
    insight = await svc.get_or_generate_for_week(user.id, WEEK_START, WEEK_END)

    assert insight.most_skipped_meal is None


@pytest.mark.anyio
async def test_late_wake_count_only_counts_replanned_events(db_session):
    user = await _make_user(db_session, "uid-ins-6")
    await _add_sleep_event(db_session, user.id, _in_week(0, hour=8), replanned=True)
    await _add_sleep_event(db_session, user.id, _in_week(1, hour=9), replanned=True)
    await _add_sleep_event(db_session, user.id, _in_week(2, hour=7), replanned=False)

    svc = InsightsService(db_session, get_llm_gateway())
    insight = await svc.get_or_generate_for_week(user.id, WEEK_START, WEEK_END)

    assert insight.late_wake_count == 2


@pytest.mark.anyio
async def test_commute_confirmed_count_excludes_pending(db_session):
    user = await _make_user(db_session, "uid-ins-7")
    await _add_commute(db_session, user.id, _in_week(0), status="confirmed")
    await _add_commute(db_session, user.id, _in_week(1), status="confirmed")
    await _add_commute(db_session, user.id, _in_week(2), status="pending")

    svc = InsightsService(db_session, get_llm_gateway())
    insight = await svc.get_or_generate_for_week(user.id, WEEK_START, WEEK_END)

    assert insight.commute_confirmed_count == 2


@pytest.mark.anyio
async def test_feedback_counts(db_session):
    user = await _make_user(db_session, "uid-ins-8")
    task = await _add_task(db_session, user.id, created_at=_in_week(0))
    await _add_feedback(db_session, user.id, task.id, "done", _in_week(0))
    await _add_feedback(db_session, user.id, task.id, "done", _in_week(1))
    await _add_feedback(db_session, user.id, task.id, "not_now", _in_week(2))

    svc = InsightsService(db_session, get_llm_gateway())
    insight = await svc.get_or_generate_for_week(user.id, WEEK_START, WEEK_END)

    assert insight.feedback_done_count == 2
    assert insight.feedback_not_now_count == 1


@pytest.mark.anyio
async def test_events_outside_week_boundary_are_excluded(db_session):
    user = await _make_user(db_session, "uid-ins-9")
    before_week = datetime(WEEK_START.year, WEEK_START.month, WEEK_START.day, tzinfo=timezone.utc) - timedelta(minutes=1)
    after_week = datetime(WEEK_END.year, WEEK_END.month, WEEK_END.day, 23, 59, 59, tzinfo=timezone.utc) + timedelta(minutes=2)
    await _add_commute(db_session, user.id, before_week, status="confirmed")
    await _add_commute(db_session, user.id, after_week, status="confirmed")

    svc = InsightsService(db_session, get_llm_gateway())
    insight = await svc.get_or_generate_for_week(user.id, WEEK_START, WEEK_END)

    assert insight.commute_confirmed_count == 0


@pytest.mark.anyio
async def test_generation_is_idempotent(db_session):
    user = await _make_user(db_session, "uid-ins-10")
    svc = InsightsService(db_session, get_llm_gateway())
    first = await svc.get_or_generate_for_week(user.id, WEEK_START, WEEK_END)
    second = await svc.get_or_generate_for_week(user.id, WEEK_START, WEEK_END)

    assert first.id == second.id


@pytest.mark.anyio
async def test_llm_failure_falls_back_to_template_summary(db_session):
    user = await _make_user(db_session, "uid-ins-11")
    await _add_task(db_session, user.id, created_at=_in_week(0), status="done", updated_at=_in_week(0))

    svc = InsightsService(db_session, get_llm_gateway())  # _NoOpProvider raises — fallback path
    insight = await svc.get_or_generate_for_week(user.id, WEEK_START, WEEK_END)

    assert "1 of 1" in insight.summary_text


@pytest.mark.anyio
async def test_llm_success_uses_generated_summary(db_session):
    class _MockProvider(_NoOpProvider):
        async def complete(self, request):
            return LLMResponse(content="You had a steady, focused week.", model="mock", provider="mock")

    set_llm_gateway(LLMGateway(provider=_MockProvider()))
    user = await _make_user(db_session, "uid-ins-12")

    svc = InsightsService(db_session, get_llm_gateway())
    insight = await svc.get_or_generate_for_week(user.id, WEEK_START, WEEK_END)

    assert insight.summary_text == "You had a steady, focused week."


def test_most_recently_completed_week_is_the_prior_monday_to_sunday():
    # Wednesday 2026-07-08 -> most recent completed week is 2026-06-29 (Mon) to 2026-07-05 (Sun)
    week_start, week_end = most_recently_completed_week(date(2026, 7, 8))
    assert week_start == date(2026, 6, 29)
    assert week_end == date(2026, 7, 5)


# ── API-layer tests (premium gate, endpoint wiring, isolation) ────────────────

MOCK_USER = TokenUser(uid="uid-insights-api-1", email="insights-api@example.com", role="user", email_verified=True)
OTHER_USER = TokenUser(uid="uid-insights-api-2", email="insights-api-other@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


async def _grant_premium(db_session, uid: str, email: str):
    user, _ = await UserService(db_session).get_or_create_user(uid, email)
    db_session.add(Subscription(user_id=user.id, status="trialing"))
    await db_session.flush()


@pytest.mark.anyio
async def test_weekly_insight_without_premium_returns_403(client, db_session):
    from tests.conftest import expire_intro_trial
    await expire_intro_trial(db_session, MOCK_USER.uid, MOCK_USER.email)
    with _mock_verify(MOCK_USER):
        r = await client.get("/api/v1/insights/weekly", headers=_auth_headers())
    assert r.status_code == 403


@pytest.mark.anyio
async def test_weekly_insight_with_premium_returns_200(client, db_session):
    await _grant_premium(db_session, MOCK_USER.uid, MOCK_USER.email)
    with _mock_verify(MOCK_USER):
        r = await client.get("/api/v1/insights/weekly", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert "summary_text" in data
    assert "week_start" in data


@pytest.mark.anyio
async def test_history_orders_most_recent_first(client, db_session):
    await _grant_premium(db_session, MOCK_USER.uid, MOCK_USER.email)
    with _mock_verify(MOCK_USER):
        r = await client.get("/api/v1/insights/history", headers=_auth_headers())
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.anyio
async def test_insights_are_per_user(client, db_session):
    await _grant_premium(db_session, MOCK_USER.uid, MOCK_USER.email)
    await _grant_premium(db_session, OTHER_USER.uid, OTHER_USER.email)

    with _mock_verify(MOCK_USER):
        await client.get("/api/v1/insights/weekly", headers=_auth_headers())

    with _mock_verify(OTHER_USER):
        history = await client.get("/api/v1/insights/history", headers=_auth_headers())
    assert history.json() == []
