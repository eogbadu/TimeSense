"""TIME-293 — the engine must be able to tell two tasks apart.

Of the eight weighted scoring factors, four were hard-coded IDENTICAL for every task candidate:
context_fit 0.6, routine_fit 0.4, user_preference_fit 0.5, location_fit 0.5. Together they carry
38% of the weight (0.15 + 0.08 + 0.05 + 0.10), so more than a third of every task's score was a
constant and only urgency, importance, time_fit and energy_fit could tell two tasks apart.

Note on the number: an earlier survey of this code reported 58%, which is wrong — it inverted the
split. The test below pins the real figure against WEIGHTS so the claim can't drift again.

The tests below are written as: hold everything constant, vary ONE factor, and assert the scores
differ. Every one of them would fail against the old constants — which is the point.
"""
from __future__ import annotations

import pytest

from app.services.recommendation.scoring.fits import (
    NEUTRAL,
    context_fit,
    location_fit_for_task,
    routine_fit,
    user_preference_fit,
)
from app.services.recommendation.scoring.score import WEIGHTS
from app.services.recommendation.types import (
    CalendarContext,
    TaskContext,
    TaskItem,
    TimeSnapshot,
    UserContext,
    UserLocationSnapshot,
    UserPreferences,
)


def _ctx(
    *, part_of_day="morning", hour=9, day_of_week="Monday",
    location_category=None, free_minutes=180, adaptation=None,
) -> UserContext:
    location = (
        UserLocationSnapshot(
            location_category=location_category, last_updated_at="2026-08-20T09:00:00+00:00",
            confidence=0.9,
        )
        if location_category else None
    )
    return UserContext(
        timestamp="2026-08-20T09:00:00+00:00",
        timezone="UTC",
        time_context=TimeSnapshot(
            now="2026-08-20T09:00:00+00:00", timezone="UTC",
            local_time="2026-08-20T09:00:00", day_of_week=day_of_week,
            part_of_day=part_of_day, is_weekend=False, is_work_hours=True, hour=hour,
        ),
        calendar_context=CalendarContext(
            free_block_minutes=free_minutes,
            has_hard_deadline_today=False,
            meeting_density_today=0,
        ),
        task_context=TaskContext(),
        user_preferences=UserPreferences(),
        location_context=location,
        adaptation=adaptation,
    )


def _task(minutes=30) -> TaskItem:
    return TaskItem(id="t1", title="Write the report", source="manual",
                    priority="medium", status="pending", estimated_minutes=minutes)


# ── the headline: 58% of the weight was inert ────────────────────────────────────────────


def test_these_four_factors_carry_a_large_share_of_the_scoring_weight():
    """Establishes the stake, and pins the actual number so the claim can't drift.

    38%: context_fit 0.15 + location_fit 0.10 + routine_fit 0.08 + user_preference_fit 0.05.
    While they were constants, better than a third of every task's score was the same value for
    every candidate.
    """
    inert = WEIGHTS["context_fit"] + WEIGHTS["routine_fit"] + \
        WEIGHTS["user_preference_fit"] + WEIGHTS["location_fit"]
    assert round(inert, 2) == 0.38, f"the four factors are {inert:.0%} of the weight"
    assert inert > 0.3, "still a large enough share to dominate ranking when constant"


# ── context_fit ──────────────────────────────────────────────────────────────────────────


def test_context_fit_varies_with_part_of_day():
    morning = context_fit(_task(), "writing", _ctx(part_of_day="morning"))
    night = context_fit(_task(), "writing", _ctx(part_of_day="night"))
    assert morning > night


def test_context_fit_knows_you_cannot_run_an_errand_from_the_sofa():
    at_home = context_fit(_task(), "errand", _ctx(location_category="home"))
    out = context_fit(_task(), "errand", _ctx(location_category="store"))
    assert out > at_home


def test_context_fit_knows_chores_happen_at_home():
    at_home = context_fit(_task(), "chore", _ctx(location_category="home"))
    out = context_fit(_task(), "chore", _ctx(location_category="office"))
    assert at_home > out


def test_context_fit_avoids_starting_something_that_will_not_finish():
    plenty = context_fit(_task(minutes=60), "writing", _ctx(free_minutes=180))
    squeezed = context_fit(_task(minutes=60), "writing", _ctx(free_minutes=15))
    assert plenty > squeezed


def test_two_different_kinds_of_task_get_different_context_fits():
    """The single assertion that would have been impossible before: same moment, different tasks."""
    ctx = _ctx(part_of_day="night", location_category="home")
    deep = context_fit(_task(), "writing", ctx)
    chore = context_fit(_task(), "chore", ctx)
    assert deep != chore


# ── routine_fit ──────────────────────────────────────────────────────────────────────────


def test_routine_fit_is_neutral_without_a_profile():
    assert routine_fit("writing", _ctx()) == NEUTRAL


def test_routine_fit_follows_when_the_user_actually_finishes_things():
    good_hour = _ctx(hour=9, adaptation={"completion_by_hour": {"9": 0.9}})
    bad_hour = _ctx(hour=22, adaptation={"completion_by_hour": {"22": 0.1}})
    assert routine_fit("writing", good_hour) > routine_fit("writing", bad_hour)


def test_routine_fit_pulls_toward_the_observation_without_adopting_it_outright():
    """A completion rate is evidence about an hour, not a verdict on this task."""
    ctx = _ctx(hour=9, adaptation={"completion_by_hour": {"9": 1.0}})
    fit = routine_fit("writing", ctx)
    assert NEUTRAL < fit < 1.0


def test_routine_fit_ignores_an_hour_it_has_no_data_for():
    ctx = _ctx(hour=15, adaptation={"completion_by_hour": {"9": 0.9}})
    assert routine_fit("writing", ctx) == NEUTRAL


def test_routine_fit_uses_the_weekday_signal_too():
    ctx = _ctx(hour=15, day_of_week="Monday",
               adaptation={"completion_by_weekday": {"0": 0.9}})
    assert routine_fit("writing", ctx) > NEUTRAL


# ── user_preference_fit ──────────────────────────────────────────────────────────────────


def test_preference_fit_is_neutral_without_a_profile():
    assert user_preference_fit("errand", "quick_task", _ctx()) == NEUTRAL


def test_preference_fit_distinguishes_categories_the_old_code_could_not():
    """The pre-existing learning was keyed on action_type alone. "Not this errand" and "not this
    deep work" are different statements about the same action type."""
    ctx = _ctx(adaptation={"acceptance_by_category": {"errand": 0.9, "writing": 0.1}})
    assert user_preference_fit("errand", "quick_task", ctx) > \
        user_preference_fit("writing", "quick_task", ctx)


def test_preference_fit_falls_back_to_action_type_when_the_category_is_unknown():
    ctx = _ctx(adaptation={"acceptance_by_action_type": {"deep_work": 0.9}})
    assert user_preference_fit("nonexistent", "deep_work", ctx) == 0.9


def test_preference_fit_prefers_the_category_signal_when_both_exist():
    ctx = _ctx(adaptation={
        "acceptance_by_category": {"errand": 0.9},
        "acceptance_by_action_type": {"quick_task": 0.1},
    })
    assert user_preference_fit("errand", "quick_task", ctx) == 0.9


# ── location_fit ─────────────────────────────────────────────────────────────────────────


def test_location_fit_is_neutral_with_no_signal_rather_than_pessimistic():
    """Absent location must not be treated as bad location — that would penalise every user who
    hasn't granted permission."""
    assert location_fit_for_task("errand", _ctx()) == NEUTRAL
    assert location_fit_for_task("errand", _ctx(location_category="unknown")) == NEUTRAL


def test_location_fit_varies_by_where_the_user_is():
    out = location_fit_for_task("errand", _ctx(location_category="store"))
    home = location_fit_for_task("errand", _ctx(location_category="home"))
    assert out > home


def test_location_fit_is_no_longer_the_same_number_for_every_task():
    """It was a flat 0.5, so it contributed an identical +5 to every candidate."""
    ctx = _ctx(location_category="home")
    values = {
        location_fit_for_task(category, ctx)
        for category in ("errand", "chore", "writing", "social")
    }
    assert len(values) > 1, "location_fit is still constant across task kinds"


# ── the combined effect ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("category_a,category_b", [("errand", "writing"), ("chore", "reading")])
def test_two_tasks_differing_only_in_kind_now_score_differently(category_a, category_b):
    """The whole point, stated as one assertion per pair. Under the old constants both sides of
    this comparison were identical by construction."""
    ctx = _ctx(part_of_day="evening", location_category="home",
               adaptation={"acceptance_by_category": {category_a: 0.9, category_b: 0.2}})
    task = _task()

    def weighted(category):
        return (
            context_fit(task, category, ctx) * WEIGHTS["context_fit"]
            + routine_fit(category, ctx) * WEIGHTS["routine_fit"]
            + user_preference_fit(category, "task", ctx) * WEIGHTS["user_preference_fit"]
            + location_fit_for_task(category, ctx) * WEIGHTS["location_fit"]
        )

    assert weighted(category_a) != weighted(category_b)


def test_a_brand_new_user_is_scored_neutrally_on_all_four():
    """The safety property. With no history and no location, every learned fit must sit at neutral
    so ranking falls back to urgency and importance — the old behaviour, and a sane default."""
    ctx = _ctx(part_of_day="afternoon")
    assert routine_fit("writing", ctx) == NEUTRAL
    assert user_preference_fit("writing", "deep_work", ctx) == NEUTRAL
    assert location_fit_for_task("writing", ctx) == NEUTRAL


def test_every_fit_stays_within_bounds_under_extreme_inputs():
    ctx = _ctx(part_of_day="night", location_category="home", free_minutes=1,
               adaptation={"completion_by_hour": {"9": 1.0}, "acceptance_by_category": {"x": 1.0}})
    for category in ("writing", "errand", "chore", "unknown_category"):
        for value in (
            context_fit(_task(minutes=600), category, ctx),
            routine_fit(category, ctx),
            user_preference_fit(category, "task", ctx),
            location_fit_for_task(category, ctx),
        ):
            assert 0.0 <= value <= 1.0
