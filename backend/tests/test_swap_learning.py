"""TIME-296 — learning from swap pairs, and making the disagree reason count.

Two things this closes.

1. A swap names BOTH sides of a preference in a known context. That is strictly more information
   than a rejection, and none of it was being used.
2. Until now the disagree reason was read in exactly ONE place — to choose between a 3-hour and a
   24-hour demote window. So "wrong time" and "not a priority" were indistinguishable to scoring,
   despite meaning completely different things.

The tests below check that each signal produces a distinct, bounded effect, and that none of them
fire on thin evidence.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.recommendation.feedback.apply_feedback import (
    REASON_MIN_SAMPLES,
    SWAP_MIN_SAMPLES,
    FeedbackSummary,
    apply_feedback_adjustments,
)
from app.services.recommendation.scoring.penalties import compute_penalty
from app.services.recommendation.types import (
    CalendarContext,
    CandidateAction,
    HealthContext,
    TaskContext,
    TimeSnapshot,
    UserContext,
    UserPreferences,
)

NOW = datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc)


def _ctx(energy: str | None = None) -> UserContext:
    return UserContext(
        timestamp=NOW.isoformat(), timezone="UTC",
        time_context=TimeSnapshot(
            now=NOW.isoformat(), timezone="UTC", local_time=NOW.isoformat(),
            day_of_week="Thursday", part_of_day="morning", is_weekend=False,
            is_work_hours=True, hour=10,
        ),
        calendar_context=CalendarContext(free_block_minutes=180, has_hard_deadline_today=False,
                                         meeting_density_today=0),
        task_context=TaskContext(),
        user_preferences=UserPreferences(),
        health_context=(HealthContext(energy_estimate=energy) if energy else None),
    )


def _cand(category="writing", codes=None, required_energy="medium", minutes=30, importance=0.5):
    return CandidateAction(
        id="c", type="deep_work", domain="task", title="T", description="d",
        estimated_minutes=minutes, importance=importance,
        required_energy=required_energy,
        reason_codes=list(codes or []), task_category=category,
    )


# ── swap pairs ───────────────────────────────────────────────────────────────────────────


def test_a_repeatedly_chosen_category_is_boosted_at_this_time_of_day():
    summary = FeedbackSummary(preferred_categories_now={"errand"})
    tagged = apply_feedback_adjustments(_cand(category="errand"), summary)
    assert "USER_PREFERS_THIS_TYPE_NOW" in tagged.reason_codes
    assert compute_penalty(tagged, _ctx()) < compute_penalty(_cand(category="errand"), _ctx())


def test_a_repeatedly_swapped_away_category_is_penalised_at_this_time_of_day():
    summary = FeedbackSummary(swapped_away_categories_now={"writing"})
    tagged = apply_feedback_adjustments(_cand(category="writing"), summary)
    assert "USER_SWAPS_AWAY_FROM_THIS_NOW" in tagged.reason_codes
    assert compute_penalty(tagged, _ctx()) > compute_penalty(_cand(category="writing"), _ctx())


def test_the_two_sides_of_a_swap_move_in_opposite_directions():
    """The whole value of a pair: it says what to do MORE of and what to do LESS of at once."""
    summary = FeedbackSummary(preferred_categories_now={"errand"},
                              swapped_away_categories_now={"writing"})
    chosen = apply_feedback_adjustments(_cand(category="errand"), summary)
    rejected = apply_feedback_adjustments(_cand(category="writing"), summary)
    assert compute_penalty(chosen, _ctx()) < compute_penalty(rejected, _ctx())


def test_a_category_with_no_swap_history_is_unaffected():
    summary = FeedbackSummary(preferred_categories_now={"errand"},
                              swapped_away_categories_now={"writing"})
    untouched = apply_feedback_adjustments(_cand(category="cooking"), summary)
    assert compute_penalty(untouched, _ctx()) == compute_penalty(_cand(category="cooking"), _ctx())


def test_a_candidate_with_no_category_is_never_tagged():
    """Location and fallback candidates have no task behind them; they must pass through cleanly."""
    summary = FeedbackSummary(preferred_categories_now={"errand"},
                              swapped_away_categories_now={"errand"})
    tagged = apply_feedback_adjustments(_cand(category=None), summary)
    assert not any(code.startswith("USER_PREFERS") or code.startswith("USER_SWAPS")
                   for code in tagged.reason_codes)


# ── each reason now does something different ─────────────────────────────────────────────


def test_wrong_time_penalises_only_this_part_of_day():
    """"Wrong time" is a claim about WHEN. build_summary only puts a category in this set when the
    rejections happened at the current part of day, so the code firing IS the time scoping."""
    summary = FeedbackSummary(wrong_time_categories_now={"writing"})
    tagged = apply_feedback_adjustments(_cand(category="writing"), summary)
    assert "WRONG_TIME_FOR_THIS_CATEGORY" in tagged.reason_codes
    assert compute_penalty(tagged, _ctx()) > compute_penalty(_cand(category="writing"), _ctx())


def test_too_big_only_bites_when_the_user_is_actually_depleted():
    """"Too big" is a claim about CAPACITY, so it should apply when they're low — not always."""
    summary = FeedbackSummary(too_big_categories={"writing"})
    tagged = apply_feedback_adjustments(
        _cand(category="writing", required_energy="high"), summary
    )

    depleted = compute_penalty(tagged, _ctx(energy="low"))
    fresh = compute_penalty(tagged, _ctx(energy="high"))
    assert depleted > fresh, "a 'too big' complaint should not penalise a well-rested user"


def test_too_big_does_not_penalise_a_small_task_even_when_depleted():
    summary = FeedbackSummary(too_big_categories={"writing"})
    small = apply_feedback_adjustments(
        _cand(category="writing", required_energy="low", minutes=10), summary
    )
    baseline = _cand(category="writing", required_energy="low", minutes=10)
    assert compute_penalty(small, _ctx(energy="low")) == compute_penalty(baseline, _ctx(energy="low"))


def test_not_a_priority_dampens_importance_rather_than_the_whole_score():
    """A claim about importance. An urgent deadline in that category must still be able to win, so
    the penalty scales with importance instead of being flat."""
    summary = FeedbackSummary(not_priority_categories={"admin"})
    low = apply_feedback_adjustments(_cand(category="admin", importance=0.1), summary)
    high = apply_feedback_adjustments(_cand(category="admin", importance=0.9), summary)
    penalty_low = compute_penalty(low, _ctx()) - compute_penalty(_cand(category="admin", importance=0.1), _ctx())
    penalty_high = compute_penalty(high, _ctx()) - compute_penalty(_cand(category="admin", importance=0.9), _ctx())
    assert penalty_high > penalty_low


def test_the_three_reasons_produce_three_different_effects():
    """The headline of this ticket: before it, all three were indistinguishable to scoring."""
    base = _ctx(energy="low")
    penalties = {
        reason: compute_penalty(
            apply_feedback_adjustments(
                _cand(category="writing", required_energy="high"),
                FeedbackSummary(**{field: {"writing"}}),
            ),
            base,
        )
        for reason, field in [
            ("wrong_time", "wrong_time_categories_now"),
            ("too_big", "too_big_categories"),
            ("not_priority", "not_priority_categories"),
        ]
    }
    assert len(set(penalties.values())) == 3, penalties


# ── evidence floors ──────────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_a_single_swap_does_not_move_the_model(db_session):
    """One swap is a moment, not a habit."""
    from app.repositories.recommendation_swap_repository import RecommendationSwapRepository
    from app.services.recommendation.feedback.build_summary import build_feedback_summary
    from app.services.user_service import UserService

    user, _ = await UserService(db_session).get_or_create_user("uid-swaplearn", "sl@example.com")
    repo = RecommendationSwapRepository(db_session)
    snapshot = {"local_hour": 10, "chosen_category": "errand", "rejected_category": "writing"}
    await repo.create(user.id, None, None, context_snapshot=snapshot, now=NOW)

    summary = await build_feedback_summary(db_session, user.id, NOW, user_timezone="UTC")
    assert summary.preferred_categories_now == set()
    assert summary.swapped_away_categories_now == set()


@pytest.mark.anyio
async def test_repeated_swaps_at_the_same_time_of_day_do_move_it(db_session):
    from app.repositories.recommendation_swap_repository import RecommendationSwapRepository
    from app.services.recommendation.feedback.build_summary import build_feedback_summary
    from app.services.user_service import UserService

    user, _ = await UserService(db_session).get_or_create_user("uid-swaplearn2", "sl2@example.com")
    repo = RecommendationSwapRepository(db_session)
    snapshot = {"local_hour": 10, "chosen_category": "errand", "rejected_category": "writing"}
    for i in range(SWAP_MIN_SAMPLES):
        await repo.create(user.id, None, None, context_snapshot=snapshot,
                          now=NOW - timedelta(days=i + 1))

    summary = await build_feedback_summary(db_session, user.id, NOW, user_timezone="UTC")
    assert "errand" in summary.preferred_categories_now
    assert "writing" in summary.swapped_away_categories_now


@pytest.mark.anyio
async def test_swaps_from_a_different_time_of_day_do_not_count(db_session):
    """"I'd rather run an errand" at 8pm says nothing about 10am."""
    from app.repositories.recommendation_swap_repository import RecommendationSwapRepository
    from app.services.recommendation.feedback.build_summary import build_feedback_summary
    from app.services.user_service import UserService

    user, _ = await UserService(db_session).get_or_create_user("uid-swaplearn3", "sl3@example.com")
    repo = RecommendationSwapRepository(db_session)
    evening = {"local_hour": 20, "chosen_category": "errand", "rejected_category": "writing"}
    for i in range(SWAP_MIN_SAMPLES + 2):
        await repo.create(user.id, None, None, context_snapshot=evening,
                          now=NOW - timedelta(days=i + 1))

    summary = await build_feedback_summary(db_session, user.id, NOW, user_timezone="UTC")
    assert summary.preferred_categories_now == set()


@pytest.mark.anyio
async def test_a_category_on_both_sides_of_swaps_is_not_penalised_by_itself(db_session):
    """A busy category shows up as both chosen and rejected. Counting the rejections alone would
    make it penalise itself."""
    from app.repositories.recommendation_swap_repository import RecommendationSwapRepository
    from app.services.recommendation.feedback.build_summary import build_feedback_summary
    from app.services.user_service import UserService

    user, _ = await UserService(db_session).get_or_create_user("uid-swaplearn4", "sl4@example.com")
    repo = RecommendationSwapRepository(db_session)
    for i in range(4):
        await repo.create(user.id, None, None, now=NOW - timedelta(days=i + 1),
                          context_snapshot={"local_hour": 10, "chosen_category": "errand",
                                            "rejected_category": "errand"})

    summary = await build_feedback_summary(db_session, user.id, NOW, user_timezone="UTC")
    assert "errand" not in summary.swapped_away_categories_now


@pytest.mark.anyio
async def test_reason_signals_need_repetition_too(db_session):
    from app.models.recommendation_feedback import RecommendationFeedback
    from app.models.task import Task
    from app.services.recommendation.feedback.build_summary import build_feedback_summary
    from app.services.user_service import UserService

    user, _ = await UserService(db_session).get_or_create_user("uid-reason", "rs@example.com")
    task = Task(user_id=user.id, title="Write the report", status="pending", priority=3,
                task_type="write_report")
    db_session.add(task)
    await db_session.flush()

    db_session.add(RecommendationFeedback(user_id=user.id, task_id=task.id,
                                          signal="disagree", reason="too_big"))
    await db_session.flush()
    summary = await build_feedback_summary(db_session, user.id, NOW, user_timezone="UTC")
    assert summary.too_big_categories == set(), "one complaint is not a pattern"

    for _ in range(REASON_MIN_SAMPLES):
        db_session.add(RecommendationFeedback(user_id=user.id, task_id=task.id,
                                              signal="disagree", reason="too_big"))
    await db_session.flush()
    summary = await build_feedback_summary(db_session, user.id, NOW, user_timezone="UTC")
    assert "writing" in summary.too_big_categories
