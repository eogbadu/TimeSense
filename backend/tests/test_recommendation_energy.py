"""TIME-290 — a task's required energy comes from its difficulty, not its length.

`task_required_energy` derived everything from estimated duration: >= 45 min was "high energy",
<= 15 min was "low". So a 90-minute flight looked demanding and a 10-minute code review trivial —
and the poor-sleep suppression rule, which keys on required_energy, protected users from the wrong
things.
"""
from __future__ import annotations

import pytest

from app.services.recommendation.candidates.common import task_required_energy
from app.services.recommendation.types import TaskItem
from app.services.task_library import classify


def _task(minutes=None, difficulty=None) -> TaskItem:
    return TaskItem(id="t", title="Something", source="manual", priority="medium",
                    status="pending", estimated_minutes=minutes, difficulty=difficulty)


@pytest.mark.parametrize("difficulty,expected", [("light", "low"), ("moderate", "medium"),
                                                 ("deep", "high")])
def test_difficulty_maps_directly_to_required_energy(difficulty, expected):
    assert task_required_energy(_task(difficulty=difficulty)) == expected


def test_a_long_light_task_is_no_longer_treated_as_demanding():
    """The concrete failure: 180 minutes of sitting on a plane is not deep work."""
    flight = _task(minutes=180, difficulty="light")
    assert task_required_energy(flight) == "low"


def test_a_short_deep_task_is_no_longer_treated_as_trivial():
    """The mirror: a 10-minute code review needs real attention."""
    review = _task(minutes=10, difficulty="deep")
    assert task_required_energy(review) == "high"


def test_duration_still_answers_for_tasks_created_before_classification_existed():
    """Rows predating TIME-285 have no difficulty. Falling back to the old heuristic is better than
    guessing "medium" for all of them."""
    assert task_required_energy(_task(minutes=90)) == "high"
    assert task_required_energy(_task(minutes=10)) == "low"
    assert task_required_energy(_task(minutes=30)) == "medium"
    assert task_required_energy(_task()) == "medium"


def test_the_library_gives_real_tasks_sensible_requirements():
    """End to end through the classifier, so the mapping is checked against real phrasings rather
    than hand-picked difficulty values."""
    assert task_required_energy(_task(difficulty=classify("Flight to Berlin").difficulty)) == "low"
    assert task_required_energy(_task(difficulty=classify("Review Tom's PR").difficulty)) == "high"
    assert task_required_energy(_task(difficulty=classify("Take out the bins").difficulty)) == "low"


# ── the per-user adjustment ──────────────────────────────────────────────────────────────


def test_no_adjustment_without_enough_evidence():
    thin = {"completions_by_energy": {"low": 2, "high": 1}}
    assert task_required_energy(_task(difficulty="deep"), thin) == "high"


def test_a_user_who_reliably_works_while_depleted_is_not_protected_from_demanding_work():
    """Someone who consistently finishes demanding work at low energy doesn't need the engine
    suppressing it for them."""
    tolerant = {"completions_by_energy": {"low": 8, "medium": 6, "high": 2}}
    assert task_required_energy(_task(difficulty="deep"), tolerant) == "medium"


def test_a_user_who_only_works_when_fresh_keeps_the_full_requirement():
    fresh_only = {"completions_by_energy": {"low": 1, "medium": 5, "high": 12}}
    assert task_required_energy(_task(difficulty="deep"), fresh_only) == "high"


def test_the_adjustment_only_ever_relaxes_never_tightens():
    """Deliberately one-directional. Relaxing lets the engine OFFER something the user can decline;
    tightening would silently HIDE work from someone whose data merely looks unusual, which is a
    much worse failure."""
    tolerant = {"completions_by_energy": {"low": 20, "medium": 1, "high": 1}}
    assert task_required_energy(_task(difficulty="light"), tolerant) == "low"
    assert task_required_energy(_task(difficulty="moderate"), tolerant) == "medium"

    intolerant = {"completions_by_energy": {"low": 0, "medium": 0, "high": 30}}
    assert task_required_energy(_task(difficulty="light"), intolerant) == "low"
    assert task_required_energy(_task(difficulty="moderate"), intolerant) == "medium"


def test_a_malformed_or_missing_profile_never_breaks_the_mapping():
    for profile in (None, {}, {"completions_by_energy": None}, {"completions_by_energy": {}}):
        assert task_required_energy(_task(difficulty="deep"), profile) == "high"


def test_an_unrecognised_difficulty_value_falls_back_rather_than_raising():
    assert task_required_energy(_task(minutes=90, difficulty="extreme")) == "high"
    assert task_required_energy(_task(minutes=5, difficulty="")) == "low"
