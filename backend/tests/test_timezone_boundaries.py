"""TIME-283 — "today" must mean the user's LOCAL day, in ANY timezone.

Deliberately parametrized over a spread of real zones rather than one: the bug was reported after a
flight to Japan, but the fix must hold for a user who is in China tomorrow, Australia the week
after, or Nigeria — and for the awkward zones (half-hour and 45-minute offsets) and DST days that a
whole-hour, US-centric assumption quietly gets wrong.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.core.localtime import (
    local_day_bounds,
    local_hour,
    local_today,
    resolve_zone,
    user_timezone_of,
)

# east of UTC, west of UTC, half-hour, 45-minute, no-DST, DST, and UTC itself
ZONES = [
    "Asia/Tokyo",        # +09, no DST, across the date line from the US
    "Asia/Shanghai",     # +08, no DST
    "Australia/Sydney",  # +10/+11, southern-hemisphere DST
    "Pacific/Auckland",  # +12/+13, furthest ahead
    "Africa/Lagos",      # +01, no DST
    "Asia/Kolkata",      # +05:30, half-hour offset
    "Asia/Kathmandu",    # +05:45, 45-minute offset
    "America/New_York",  # -05/-04, northern DST
    "America/Los_Angeles",
    "UTC",
]


@pytest.mark.parametrize("tz", ZONES)
def test_day_bounds_are_exactly_one_calendar_day(tz):
    start, end = local_day_bounds(date(2026, 8, 28), tz)
    assert start < end
    assert (end - start) == timedelta(days=1)
    # Both ends are returned in UTC so they can go straight into a query.
    assert start.tzinfo is timezone.utc and end.tzinfo is timezone.utc
    # Midnight local, by construction.
    assert start.astimezone(resolve_zone(tz)).hour == 0
    assert start.astimezone(resolve_zone(tz)).minute == 0


@pytest.mark.parametrize("tz", ZONES)
def test_every_instant_of_a_local_day_falls_inside_its_own_bounds(tz):
    """The property that actually matters: a task at any local hour must land in that local day."""
    day = date(2026, 8, 28)
    start, end = local_day_bounds(day, tz)
    zone = resolve_zone(tz)
    for hour in range(24):
        instant = datetime(2026, 8, 28, hour, 30, tzinfo=zone).astimezone(timezone.utc)
        assert start <= instant < end, f"{tz} {hour}:30 local fell outside its own day"


def test_tokyo_day_starts_on_the_previous_utc_date():
    """The reported bug, concretely: Tokyo's day begins at 15:00 UTC the day before."""
    start, end = local_day_bounds(date(2026, 8, 28), "Asia/Tokyo")
    assert start == datetime(2026, 8, 27, 15, 0, tzinfo=timezone.utc)
    assert end == datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc)


def test_a_tokyo_morning_task_is_not_lost_to_the_previous_utc_day():
    """East of UTC the break is in the MORNING: 7am on the 28th in Tokyo is still the 27th in UTC.
    A UTC-day query for the 28th missed it entirely — the Japan symptom."""
    zone = resolve_zone("Asia/Tokyo")
    morning = datetime(2026, 8, 28, 7, 0, tzinfo=zone).astimezone(timezone.utc)
    assert morning.date() == date(2026, 8, 27)          # a different UTC date...
    start, end = local_day_bounds(date(2026, 8, 28), "Asia/Tokyo")
    assert start <= morning < end                        # ...but still the user's 28th


def test_a_los_angeles_evening_task_is_not_pushed_into_the_next_utc_day():
    """West of UTC the break is in the EVENING, so the fix isn't accidentally east-only:
    9pm on the 28th in Los Angeles is already the 29th in UTC."""
    zone = resolve_zone("America/Los_Angeles")
    evening = datetime(2026, 8, 28, 21, 0, tzinfo=zone).astimezone(timezone.utc)
    assert evening.date() == date(2026, 8, 29)
    start, end = local_day_bounds(date(2026, 8, 28), "America/Los_Angeles")
    assert start <= evening < end


def test_the_same_instant_is_a_different_day_for_two_travellers():
    """One UTC moment, three users — each one's 'today' is their own."""
    instant = datetime(2026, 8, 28, 22, 0, tzinfo=timezone.utc)
    assert local_today("Asia/Tokyo", instant) == date(2026, 8, 29)          # already tomorrow
    assert local_today("UTC", instant) == date(2026, 8, 28)
    assert local_today("America/Los_Angeles", instant) == date(2026, 8, 28)


@pytest.mark.parametrize(
    "day,expected_hours",
    [(date(2026, 3, 8), 23), (date(2026, 11, 1), 25)],
)
def test_dst_transition_days_are_not_forced_to_24_hours(day, expected_hours):
    """A spring-forward day is 23h and a fall-back day 25h. Adding timedelta(hours=24) instead of a
    calendar day would silently clip or overlap an hour of the user's schedule."""
    start, end = local_day_bounds(day, "America/New_York")
    assert (end - start).total_seconds() / 3600 == expected_hours


def test_unknown_or_missing_timezone_degrades_to_utc_without_raising():
    for bad in ["Not/AZone", "", None, "Mars/Olympus_Mons"]:
        start, end = local_day_bounds(date(2026, 8, 28), bad)
        assert start == datetime(2026, 8, 28, tzinfo=timezone.utc)
        assert (end - start) == timedelta(days=1)


@pytest.mark.parametrize("tz", ZONES)
def test_local_today_matches_the_zone(tz):
    now = datetime(2026, 8, 28, 2, 0, tzinfo=timezone.utc)
    assert local_today(tz, now) == now.astimezone(resolve_zone(tz)).date()


def test_local_hour_identifies_each_users_own_morning():
    """What the hourly check-in worker relies on: at one UTC instant, different users are at
    different local hours, and exactly the right ones match a target hour."""
    now = datetime(2026, 8, 28, 23, 0, tzinfo=timezone.utc)
    assert local_hour("Asia/Tokyo", now) == 8            # 8am in Tokyo
    assert local_hour("America/New_York", now) == 19     # 7pm in New York
    assert local_hour("UTC", now) == 23
    morning = [tz for tz in ZONES if local_hour(tz, now) == 8]
    assert "Asia/Tokyo" in morning
    assert "America/New_York" not in morning


def test_user_timezone_of_defaults_to_utc():
    class _P:
        timezone = "Asia/Tokyo"

    class _U:
        profile = _P()

    class _NoProfile:
        profile = None

    assert user_timezone_of(_U()) == "Asia/Tokyo"
    assert user_timezone_of(_NoProfile()) == "UTC"


def test_weekly_insight_window_covers_the_users_whole_local_week():
    """TIME-283: the weekly rollup window is built from the user's local day bounds, so a task
    finished at 11pm local on the final Sunday belongs to that week, not the next one.

    Covered here rather than in test_insights.py, which cannot run in this environment (see
    known_issues.md — it blocks on the LLM provider).
    """
    from app.services.insights_service import most_recently_completed_week

    for tz in ZONES:
        week_start, week_end = most_recently_completed_week(date(2026, 8, 28))
        assert week_start == date(2026, 8, 17)   # Monday
        assert week_end == date(2026, 8, 23)     # Sunday

        start_dt, _ = local_day_bounds(week_start, tz)
        _, end_dt = local_day_bounds(week_end, tz)

        # Exactly seven local days, whatever the offset or DST.
        assert (end_dt - start_dt) == timedelta(days=7), tz

        zone = resolve_zone(tz)
        first_moment = datetime(2026, 8, 17, 0, 0, tzinfo=zone).astimezone(timezone.utc)
        last_moment = datetime(2026, 8, 23, 23, 59, tzinfo=zone).astimezone(timezone.utc)
        assert start_dt <= first_moment < end_dt, tz
        assert start_dt <= last_moment < end_dt, tz


def test_weekly_insight_window_differs_between_zones():
    """Sanity that the window is actually zone-dependent — otherwise the test above would pass
    against the old UTC-only code."""
    from app.services.insights_service import most_recently_completed_week

    week_start, week_end = most_recently_completed_week(date(2026, 8, 28))
    tokyo_start, _ = local_day_bounds(week_start, "Asia/Tokyo")
    utc_start, _ = local_day_bounds(week_start, "UTC")
    la_start, _ = local_day_bounds(week_start, "America/Los_Angeles")
    assert tokyo_start < utc_start < la_start
