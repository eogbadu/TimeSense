"""Tests for the scheduling core (TIME-084)."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

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
