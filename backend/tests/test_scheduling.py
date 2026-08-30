"""Tests for the scheduling core (TIME-084)."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.services.scheduling_service import SchedulingService

UTC = timezone.utc


def _blk(start: datetime, end: datetime):
    return SimpleNamespace(scheduled_start=start, scheduled_end=end)


def test_find_slot_no_conflicts():
    svc = SchedulingService()
    # 2026-07-06 14:00 UTC (10:00 in America/New_York, EDT) — inside the 8–21 window.
    now = datetime(2026, 7, 6, 14, 0, tzinfo=UTC)
    slot = svc.find_slot(now, 30, [], tz_name="America/New_York")
    assert slot == now  # nothing scheduled → start now


def test_find_slot_skips_busy_block():
    svc = SchedulingService()
    now = datetime(2026, 7, 6, 14, 0, tzinfo=UTC)
    # busy from now to +40 min → a 30-min task can't start until the block ends
    busy = [_blk(now, now + timedelta(minutes=40))]
    slot = svc.find_slot(now, 30, busy, tz_name="America/New_York")
    assert slot == now + timedelta(minutes=40)


def test_free_minutes_before_deadline():
    svc = SchedulingService()
    now = datetime(2026, 7, 6, 14, 0, tzinfo=UTC)
    deadline = now + timedelta(minutes=60)
    # 20 min meeting inside the hour → 40 free before the deadline
    busy = [_blk(now + timedelta(minutes=10), now + timedelta(minutes=30))]
    assert svc.free_minutes_before(deadline, now, busy, tz_name="America/New_York") == 40


def test_find_slot_outside_window_returns_none():
    svc = SchedulingService()
    # 2026-07-06 03:00 UTC = 23:00 previous day in NY → past the 21:00 window end.
    now = datetime(2026, 7, 6, 3, 0, tzinfo=UTC)
    assert svc.find_slot(now, 30, [], tz_name="America/New_York") is None


# --- TIME-308: availability vs feasibility -------------------------------------------------------
# A user at 00:03 was told "780 minutes free before your workday ends" — the whole 08:00-21:00
# workday, offered as time available right now. free_minutes_before clamps its start forward to the
# beginning of the window, which is correct for "will there be enough time before this is due" and
# wrong for "how much time do you have now". These pin both questions.

def _ny(y, m, d, hour, minute=0):
    """A local New York wall-clock time, as UTC."""
    return datetime(y, m, d, hour, minute, tzinfo=ZoneInfo("America/New_York")).astimezone(UTC)


def test_free_minutes_before_still_counts_the_workday_ahead():
    """Feasibility must keep seeing the day ahead — this is the behaviour we are NOT changing."""
    svc = SchedulingService()
    now = _ny(2026, 8, 30, 0, 3)
    assert svc.free_minutes_before(_ny(2026, 8, 30, 21), now, [], "America/New_York") == 780


def test_free_minutes_available_now_is_zero_before_the_workday_opens():
    """The reported bug, at the exact hour it was reported."""
    svc = SchedulingService()
    now = _ny(2026, 8, 30, 0, 3)
    assert svc.free_minutes_available_now(_ny(2026, 8, 30, 21), now, [], "America/New_York") == 0


def test_free_minutes_available_now_is_zero_at_dawn():
    svc = SchedulingService()
    now = _ny(2026, 8, 30, 6)
    assert svc.free_minutes_available_now(_ny(2026, 8, 30, 21), now, [], "America/New_York") == 0


def test_free_minutes_available_now_matches_free_minutes_during_the_workday():
    """Inside working hours the two questions have the same answer — no regression at 2pm."""
    svc = SchedulingService()
    now = _ny(2026, 8, 30, 14)
    deadline = _ny(2026, 8, 30, 15)
    busy = [_blk(now + timedelta(minutes=10), now + timedelta(minutes=30))]
    assert svc.free_minutes_available_now(deadline, now, busy, "America/New_York") == 40
    assert svc.free_minutes_before(deadline, now, busy, "America/New_York") == 40


def test_free_minutes_available_now_is_zero_after_hours():
    """The after-hours case already worked; keep it that way."""
    svc = SchedulingService()
    now = _ny(2026, 8, 30, 22)
    assert svc.free_minutes_available_now(_ny(2026, 8, 30, 23), now, [], "America/New_York") == 0


def test_within_working_hours_boundaries():
    svc = SchedulingService()
    tz = "America/New_York"
    assert svc.within_working_hours(_ny(2026, 8, 30, 8), tz) is True       # opens inclusive
    assert svc.within_working_hours(_ny(2026, 8, 30, 20, 59), tz) is True
    assert svc.within_working_hours(_ny(2026, 8, 30, 21), tz) is False     # closes exclusive
    assert svc.within_working_hours(_ny(2026, 8, 30, 7, 59), tz) is False
