"""TIME-288 — energy as a recovery budget that depletes.

The reported bug: TimeSense announced HIGH energy late in the evening after a busy day, and
recommended something demanding on that basis. The cause was two disagreeing implementations —
the scorer used sleep alone (hard-coded "medium" without a sample), while the display derived energy
from ACTIVITY, where 30+ minutes of exercise or 8000+ steps counted as high.

These tests pin the direction of the model, not its exact constants: what must stay true is that
spending capacity lowers it, and that the two consumers can never disagree again.
"""
from __future__ import annotations

import pytest

from app.services.energy_service import (
    ENERGY_RANK,
    HIGH,
    LOW,
    MEDIUM,
    EnergyInputs,
    circadian_modifier,
    compute_energy,
    sleep_budget,
)


def _energy(**kwargs) -> str:
    return compute_energy(EnergyInputs(**kwargs)).level


def _score(**kwargs) -> float:
    return compute_energy(EnergyInputs(**kwargs)).score


# ── the reported bug ─────────────────────────────────────────────────────────────────────


def test_a_busy_day_is_low_energy_in_the_evening():
    """THE REPORTED CASE. Slept moderately, awake 13 hours, worked out, walked a lot, sat through
    five hours of commitments — at 8pm this is not high energy."""
    assert _energy(
        local_hour=20, sleep_hours=6.5, hours_awake=13,
        exercise_minutes=45, steps=13000, sedentary_minutes=200, committed_minutes_today=300,
    ) == LOW


def test_a_well_slept_quiet_morning_is_high_energy():
    assert _energy(local_hour=9, sleep_hours=8, hours_awake=2) == HIGH


def test_activity_lowers_energy_rather_than_raising_it():
    """The inversion, isolated. Under the old rule more exercise and more steps meant MORE energy."""
    base = _score(local_hour=17, sleep_hours=7.5, hours_awake=10)
    busy = _score(local_hour=17, sleep_hours=7.5, hours_awake=10,
                  exercise_minutes=60, steps=15000)
    assert busy < base, "a day spent moving should leave less capacity, not more"


def test_committed_time_already_spent_lowers_energy():
    quiet = _score(local_hour=16, sleep_hours=7, hours_awake=9)
    packed = _score(local_hour=16, sleep_hours=7, hours_awake=9, committed_minutes_today=300)
    assert packed < quiet


def test_a_long_sedentary_stretch_is_a_drain_not_evidence_of_low_capacity():
    """Sitting for hours is depleting in its own right — but it is a small CAUSE, not the old rule's
    PROOF that the user has no energy."""
    moving = _score(local_hour=15, sleep_hours=7.5, hours_awake=8, sedentary_minutes=30)
    sitting = _score(local_hour=15, sleep_hours=7.5, hours_awake=8, sedentary_minutes=360)
    assert sitting < moving
    assert compute_energy(EnergyInputs(local_hour=15, sleep_hours=7.5, hours_awake=8,
                                       sedentary_minutes=360)).level != LOW


# ── time of day ──────────────────────────────────────────────────────────────────────────


def test_the_same_night_of_sleep_does_not_yield_the_same_energy_all_day():
    """The old model had no time dimension at all: 8am and 8pm on one night's sleep were identical."""
    morning = _score(local_hour=9, sleep_hours=8, hours_awake=2)
    evening = _score(local_hour=20, sleep_hours=8, hours_awake=13)
    assert morning > evening


def test_energy_declines_monotonically_through_an_otherwise_identical_day():
    scores = [
        _score(local_hour=h, sleep_hours=7.5, hours_awake=max(0, h - 7))
        for h in (9, 11, 16, 19, 22)
    ]
    assert scores == sorted(scores, reverse=True), scores


def test_the_middle_of_the_night_is_never_a_high_energy_window():
    for hour in (1, 2, 3, 4):
        assert _energy(local_hour=hour, sleep_hours=8) != HIGH
    assert circadian_modifier(3) < circadian_modifier(10)


def test_there_is_a_post_lunch_dip():
    assert circadian_modifier(14) < circadian_modifier(11)
    assert circadian_modifier(14) < circadian_modifier(16)


# ── sleep ────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "hours,expected_quality", [(9, "good"), (8, "good"), (7.5, "good"), (6.5, "okay"),
                               (5.5, "poor"), (3, "poor")],
)
def test_sleep_quality_bands(hours, expected_quality):
    _, quality = sleep_budget(hours)
    assert quality == expected_quality


def test_more_sleep_never_lowers_the_budget():
    budgets = [sleep_budget(h)[0] for h in (3, 5, 6, 7, 8, 9)]
    assert budgets == sorted(budgets)


def test_poor_sleep_cannot_produce_high_energy_even_first_thing():
    assert _energy(local_hour=8, sleep_hours=4, hours_awake=1) != HIGH


# ── degradation and safety ───────────────────────────────────────────────────────────────


def test_no_health_data_still_produces_a_reasoned_estimate():
    """The old code hard-coded "medium" whenever there was no sleep sample. Time of day alone is
    strictly more informative than a constant."""
    morning = compute_energy(EnergyInputs(local_hour=10))
    night = compute_energy(EnergyInputs(local_hour=23))
    assert morning.level != LOW
    assert night.level == LOW
    assert morning.source == "time_of_day"
    assert morning.reason


def test_high_energy_is_never_claimed_without_sleep_evidence():
    """"High energy" invites starting something demanding. Don't assert it from the clock alone."""
    for hour in range(0, 24):
        assert _energy(local_hour=hour) != HIGH, f"claimed high energy at {hour}:00 with no data"


def test_the_score_is_always_a_valid_bounded_number():
    extremes = [
        EnergyInputs(local_hour=0),
        EnergyInputs(local_hour=23.99, sleep_hours=0, hours_awake=48,
                     exercise_minutes=600, steps=99999, sedentary_minutes=1440,
                     committed_minutes_today=1440),
        EnergyInputs(local_hour=6, sleep_hours=24, hours_awake=0),
    ]
    for inputs in extremes:
        estimate = compute_energy(inputs)
        assert 0.0 <= estimate.score <= 1.0
        assert estimate.level in ENERGY_RANK


# ── the two consumers can no longer disagree ─────────────────────────────────────────────


def test_the_canonical_level_is_always_rankable_by_the_engine():
    """The display layer used "moderate" where the engine's rank map expects "medium". That would
    have raised a KeyError; it only avoided one because the engine never saw the display's value."""
    for hour in range(0, 24):
        for sleep in (None, 4, 6, 8):
            estimate = compute_energy(EnergyInputs(local_hour=hour, sleep_hours=sleep))
            assert estimate.level in ENERGY_RANK, estimate.level


def test_display_wording_is_separate_from_the_canonical_value():
    """Copy reads better as "moderate"; the engine must only ever see "medium". One translation
    point means they cannot drift apart again."""
    estimate = compute_energy(EnergyInputs(local_hour=14, sleep_hours=7))
    assert estimate.level == MEDIUM
    assert estimate.display_label == "moderate"
    assert estimate.level in ENERGY_RANK


@pytest.mark.anyio
async def test_the_scorer_and_the_why_sheet_report_the_same_energy(db_session):
    """The structural point of the ticket: one implementation, so the card can never show one thing
    while the recommendation is based on another."""
    from datetime import UTC, datetime

    from app.repositories.daily_activity_repository import DailyActivityRepository
    from app.services.energy_service import EnergyService
    from app.services.recommendation.context_builder import _health as engine_health
    from app.services.recommendation_explainer import _health as sheet_health
    from app.services.user_service import UserService

    user, _ = await UserService(db_session).get_or_create_user("uid-energy-1", "e1@example.com")
    now = datetime(2026, 8, 1, 20, 0, tzinfo=UTC)
    await DailyActivityRepository(db_session).upsert(
        user.id, now.date(), steps=14000, active_energy_kcal=None,
        exercise_minutes=60, inactive_minutes=120,
    )

    canonical = await EnergyService(db_session).estimate(user.id, now=now, user_timezone="UTC")
    engine = await engine_health(db_session, user.id, now, "UTC")
    sheet = await sheet_health(db_session, user.id, now, "UTC")

    assert engine is not None and sheet is not None
    assert engine.energy_estimate == canonical.level
    assert sheet["level"] == canonical.level
    assert sheet["energy"] == canonical.display_label


@pytest.mark.anyio
async def test_committed_time_is_counted_only_once_it_has_actually_been_spent(db_session):
    """A back-to-back morning should show as depletion by mid-afternoon — but a meeting still ahead
    of the user has cost them nothing yet, so it must not count."""
    from datetime import UTC, datetime, timedelta

    from app.models.task import Task
    from app.services.energy_service import EnergyService
    from app.services.user_service import UserService

    user, _ = await UserService(db_session).get_or_create_user("uid-energy-2", "e2@example.com")
    now = datetime(2026, 8, 3, 15, 0, tzinfo=UTC)

    # Three hours of work finished this morning...
    db_session.add(Task(
        user_id=user.id, title="Write the report", status="done", priority=2,
        scheduled_start=now - timedelta(hours=5), scheduled_end=now - timedelta(hours=2),
    ))
    # ...and two hours still to come this evening.
    db_session.add(Task(
        user_id=user.id, title="Client meeting with Acme", status="pending", priority=2,
        scheduled_start=now + timedelta(hours=2), scheduled_end=now + timedelta(hours=4),
    ))
    await db_session.flush()

    spent = await EnergyService(db_session)._committed_minutes(user.id, now.date(), now, "UTC")
    assert spent == 180, "only the finished block should count"
