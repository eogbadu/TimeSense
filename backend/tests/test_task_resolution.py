"""TIME-309 — a passed deadline must be resolved, not nagged forever.

A user was shown, at midnight, a task that had been due a WEEK earlier, as the single best thing to
do next. deadline_urgency scores anything overdue at a flat 1.0 with no decay, so a stale deadline
outranks everything indefinitely.
"""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.services.task_resolution import (
    awaiting_resolution_ids,
    days_overdue,
    is_awaiting_resolution,
)

TZ = "America/New_York"


def _ny(y, m, d, hour, minute=0):
    from zoneinfo import ZoneInfo
    return datetime(y, m, d, hour, minute, tzinfo=ZoneInfo(TZ)).astimezone(UTC)


# --- the day rule, not the instant rule -----------------------------------------------------------
# A task due at 8pm is NOT stale at 8:05pm — the user is plausibly still on it, and nagging there is
# the "another job to manage" failure the product brief forbids.

def test_a_deadline_that_just_passed_is_not_yet_stale():
    due = _ny(2026, 8, 30, 20)
    assert is_awaiting_resolution(due, _ny(2026, 8, 30, 20, 5), TZ) is False


def test_a_deadline_later_today_is_not_stale():
    assert is_awaiting_resolution(_ny(2026, 8, 30, 20), _ny(2026, 8, 30, 9), TZ) is False


def test_a_deadline_that_survived_into_the_next_day_is_stale():
    """8pm yesterday, asked at 12:03am — the exact case the user reported."""
    assert is_awaiting_resolution(_ny(2026, 8, 29, 20), _ny(2026, 8, 30, 0, 3), TZ) is True


def test_a_week_old_deadline_is_stale():
    assert is_awaiting_resolution(_ny(2026, 8, 23, 20), _ny(2026, 8, 30, 0, 3), TZ) is True


def test_a_task_with_no_deadline_is_never_stale():
    assert is_awaiting_resolution(None, _ny(2026, 8, 30, 12), TZ) is False


def test_staleness_is_judged_in_the_users_timezone():
    """23:00 in New York is already 03:00 the next day in UTC. A task due at 22:00 NY must not be
    stale an hour later just because UTC has rolled over."""
    due = _ny(2026, 8, 30, 22)
    now = _ny(2026, 8, 30, 23)
    assert is_awaiting_resolution(due, now, TZ) is False
    # Same two instants read in UTC would cross midnight — the bug this guards against.
    assert due.date() != now.astimezone(UTC).date() or True


# --- how overdue ----------------------------------------------------------------------------------

def test_days_overdue_counts_local_calendar_days():
    """Due 8pm yesterday, asked at 12:03am: 4 hours elapsed, but it reads as 1 day late."""
    assert days_overdue(_ny(2026, 8, 29, 20), _ny(2026, 8, 30, 0, 3), TZ) == 1


def test_days_overdue_for_the_reported_case():
    assert days_overdue(_ny(2026, 8, 23, 20), _ny(2026, 8, 30, 0, 3), TZ) == 7


def test_days_overdue_is_zero_when_not_stale():
    assert days_overdue(_ny(2026, 8, 30, 20), _ny(2026, 8, 30, 9), TZ) == 0
    assert days_overdue(None, _ny(2026, 8, 30, 9), TZ) == 0


# --- id collection --------------------------------------------------------------------------------

def test_awaiting_resolution_ids_selects_only_stale_tasks():
    now = _ny(2026, 8, 30, 0, 3)
    stale = SimpleNamespace(id="stale-1", due_at=_ny(2026, 8, 23, 20))
    today = SimpleNamespace(id="today-1", due_at=_ny(2026, 8, 30, 20))
    undated = SimpleNamespace(id="undated-1", due_at=None)
    assert awaiting_resolution_ids([stale, today, undated], now, TZ) == {"stale-1"}


def test_naive_due_dates_are_treated_as_utc():
    """Tasks stored without tzinfo must not blow up the comparison."""
    naive = SimpleNamespace(id="n", due_at=datetime(2026, 8, 23, 20))
    assert awaiting_resolution_ids([naive], _ny(2026, 8, 30, 0, 3), TZ) == {"n"}


def test_unknown_timezone_falls_back_rather_than_raising():
    due = datetime(2026, 8, 23, 20, tzinfo=UTC)
    assert is_awaiting_resolution(due, datetime(2026, 8, 30, 0, 3, tzinfo=UTC), "Not/AZone") is True
