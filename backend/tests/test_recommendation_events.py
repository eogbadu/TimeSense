"""Tests for the RecommendationEvent impression→outcome repository (TIME-196)."""
import uuid

import pytest

from app.models.recommendation_event import RecommendationEvent  # noqa: F401 — register the table
from app.models.task import Task
from app.models.user import User
from app.repositories.recommendation_event_repository import RecommendationEventRepository


async def _user_and_task(db_session, uid="rev-1"):
    user = User(firebase_uid=uid, email=f"{uid}@example.com")
    db_session.add(user)
    await db_session.flush()
    task = Task(user_id=user.id, title="Draft doc", status="pending")
    db_session.add(task)
    await db_session.flush()
    return user, task


@pytest.mark.anyio
async def test_record_impression_inserts_with_typed_columns(db_session):
    user, task = await _user_and_task(db_session)
    repo = RecommendationEventRepository(db_session)
    ev = await repo.record_impression(
        user.id, task.id, surface="now", confidence=0.8,
        action_type="deep_work", domain="task", score=0.72, rank=0,
    )
    assert ev.id is not None
    assert ev.surface == "now" and ev.action_type == "deep_work" and ev.domain == "task"
    assert ev.score == 0.72 and ev.outcome is None


@pytest.mark.anyio
async def test_record_impression_dedupes_within_window(db_session):
    user, task = await _user_and_task(db_session, "rev-2")
    repo = RecommendationEventRepository(db_session)
    ev1 = await repo.record_impression(user.id, task.id, surface="now", confidence=0.8)
    ev2 = await repo.record_impression(user.id, task.id, surface="now", confidence=0.9)
    assert ev1.id == ev2.id  # one impression per shown pick within the window


@pytest.mark.anyio
async def test_record_impression_new_after_outcome(db_session):
    user, task = await _user_and_task(db_session, "rev-3")
    repo = RecommendationEventRepository(db_session)
    ev1 = await repo.record_impression(user.id, task.id, surface="now", confidence=0.8)
    await repo.set_outcome(ev1.id, user.id, outcome="done")
    ev2 = await repo.record_impression(user.id, task.id, surface="now", confidence=0.8)
    assert ev2.id != ev1.id  # a resolved impression doesn't suppress a fresh one


@pytest.mark.anyio
async def test_set_outcome(db_session):
    user, task = await _user_and_task(db_session, "rev-4")
    repo = RecommendationEventRepository(db_session)
    ev = await repo.record_impression(user.id, task.id, surface="now", confidence=0.8)
    fb_id = uuid.uuid4()
    ok = await repo.set_outcome(ev.id, user.id, outcome="agree", feedback_id=fb_id)
    assert ok is True
    assert ev.outcome == "agree" and ev.outcome_at is not None and ev.feedback_id == fb_id


@pytest.mark.anyio
async def test_set_outcome_unknown_event_returns_false(db_session):
    user, _ = await _user_and_task(db_session, "rev-5")
    repo = RecommendationEventRepository(db_session)
    assert await repo.set_outcome(uuid.uuid4(), user.id, outcome="done") is False


@pytest.mark.anyio
async def test_build_feedback_summary_counts_by_action_type(db_session):
    from app.services.recommendation.feedback.build_summary import build_feedback_summary

    user, task = await _user_and_task(db_session, "rev-fb")
    repo = RecommendationEventRepository(db_session)
    for outcome in ("disagree", "disagree", "disagree", "agree"):
        ev = await repo.record_impression(user.id, task.id, surface="now", confidence=0.8, action_type="deep_work")
        await repo.set_outcome(ev.id, user.id, outcome=outcome)
    ev2 = await repo.record_impression(user.id, task.id, surface="now_recommendation", confidence=0.8, action_type="run_errand")
    await repo.set_outcome(ev2.id, user.id, outcome="done")

    summary = await build_feedback_summary(db_session, user.id)
    assert summary.rejects.get("deep_work") == 3
    assert summary.accepts.get("deep_work") == 1
    assert summary.accepts.get("run_errand") == 1
    assert "deep_work" in summary.recently_dismissed  # the disagrees are recent
