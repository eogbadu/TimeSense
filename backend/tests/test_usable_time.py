from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.usable_time_service import UsableTimeService


def _task(start_offset_min: int, end_offset_min: int, anchor: datetime) -> SimpleNamespace:
    """Create a lightweight stand-in with only the fields UsableTimeService reads."""
    return SimpleNamespace(
        scheduled_start=anchor + timedelta(minutes=start_offset_min),
        scheduled_end=anchor + timedelta(minutes=end_offset_min),
        status="pending",
    )


ANCHOR = datetime(2026, 7, 3, 14, 0, 0, tzinfo=timezone.utc)  # 14:00 UTC, 10h until midnight


class TestUsableTimeService:
    svc = UsableTimeService()

    def test_no_tasks_returns_capped_window(self) -> None:
        result = self.svc.calculate([], anchor=ANCHOR)
        assert result == UsableTimeService.MAX_WINDOW_MINUTES

    def test_task_starts_in_future_returns_gap(self) -> None:
        task = _task(30, 90, ANCHOR)  # starts in 30 min
        result = self.svc.calculate([task], anchor=ANCHOR)
        assert result == 30

    def test_task_in_progress_returns_gap_after_it(self) -> None:
        # Task spans -10 to +50 (currently in progress); next gap = 50 min to midnight
        task = _task(-10, 50, ANCHOR)
        result = self.svc.calculate([task], anchor=ANCHOR)
        # gap after task ends at ANCHOR+50 min; until midnight = (10*60 - 50) = 550 min → capped
        assert result == UsableTimeService.MAX_WINDOW_MINUTES

    def test_task_already_ended_ignored(self) -> None:
        task = _task(-90, -30, ANCHOR)  # ended 30 min ago
        result = self.svc.calculate([task], anchor=ANCHOR)
        assert result == UsableTimeService.MAX_WINDOW_MINUTES

    def test_overlapping_tasks_merged(self) -> None:
        # Two overlapping blocks: [+20, +60] and [+45, +80] → merged [+20, +80] → gap=20
        t1 = _task(20, 60, ANCHOR)
        t2 = _task(45, 80, ANCHOR)
        result = self.svc.calculate([t1, t2], anchor=ANCHOR)
        assert result == 20

    def test_adjacent_tasks_merged(self) -> None:
        # [+10, +30] and [+30, +60] → merged [+10, +60] → gap=10
        t1 = _task(10, 30, ANCHOR)
        t2 = _task(30, 60, ANCHOR)
        result = self.svc.calculate([t1, t2], anchor=ANCHOR)
        assert result == 10

    def test_small_gap_returns_zero(self) -> None:
        # Task starts in 3 min → below MIN_WINDOW_MINUTES (5) → 0
        task = _task(3, 60, ANCHOR)
        result = self.svc.calculate([task], anchor=ANCHOR)
        assert result == 0

    def test_cap_at_max_window(self) -> None:
        # Task starts 5 hours from now → gap capped at MAX_WINDOW_MINUTES
        task = _task(300, 360, ANCHOR)
        result = self.svc.calculate([task], anchor=ANCHOR)
        assert result == UsableTimeService.MAX_WINDOW_MINUTES

    def test_tasks_without_end_time_ignored(self) -> None:
        t = SimpleNamespace(
            scheduled_start=ANCHOR + timedelta(minutes=30),
            scheduled_end=None,
            status="pending",
        )
        result = self.svc.calculate([t], anchor=ANCHOR)
        assert result == UsableTimeService.MAX_WINDOW_MINUTES

    def test_end_of_day_capped_at_midnight(self) -> None:
        # Anchor is 23:45 → only 15 min until midnight; no tasks
        late = datetime(2026, 7, 3, 23, 45, 0, tzinfo=timezone.utc)
        result = self.svc.calculate([], anchor=late)
        assert result == 15

    def test_gap_between_two_back_to_back_meetings(self) -> None:
        # Meeting 1: +0 to +60; Meeting 2: +90 to +120 → gap of 30 min between them
        # But we're currently in meeting 1 (it starts at anchor +0 = now)
        t1 = _task(0, 60, ANCHOR)
        t2 = _task(90, 120, ANCHOR)
        result = self.svc.calculate([t1, t2], anchor=ANCHOR)
        # currently in t1 (start == now); after t1 ends at +60, next block at +90 → 30 min gap
        assert result == 30


def _event(start_offset_min: int, end_offset_min: int, anchor: datetime, all_day: bool = False):
    """A calendar-event stand-in with only the fields UsableTimeService reads (TIME-275)."""
    return SimpleNamespace(
        starts_at=anchor + timedelta(minutes=start_offset_min),
        ends_at=anchor + timedelta(minutes=end_offset_min),
        all_day=all_day,
    )


class TestUsableTimeCalendarEvents:
    """TIME-275: calendar meetings block usable time alongside scheduled tasks."""

    svc = UsableTimeService()

    def test_calendar_event_blocks_time_like_a_task(self) -> None:
        # A meeting starting in 30 min, no tasks → 30 min usable (same as a task would give).
        result = self.svc.calculate([], anchor=ANCHOR, events=[_event(30, 90, ANCHOR)])
        assert result == 30

    def test_all_day_event_ignored(self) -> None:
        # An all-day event doesn't consume a working slot.
        result = self.svc.calculate([], anchor=ANCHOR, events=[_event(0, 1440, ANCHOR, all_day=True)])
        assert result == UsableTimeService.MAX_WINDOW_MINUTES

    def test_event_overlapping_task_not_double_counted(self) -> None:
        # Imported meeting exists as BOTH a task and an event over [+20,+60] → they merge → gap 20.
        task = _task(20, 60, ANCHOR)
        event = _event(20, 60, ANCHOR)
        assert self.svc.calculate([task], anchor=ANCHOR, events=[event]) == 20

    def test_event_soonest_wins_over_later_task(self) -> None:
        # Task at +50, meeting at +25 → the meeting is the nearer block → gap 25.
        task = _task(50, 80, ANCHOR)
        event = _event(25, 45, ANCHOR)
        assert self.svc.calculate([task], anchor=ANCHOR, events=[event]) == 25


def test_end_of_day_cap_uses_local_midnight():
    """The 'time left today' cap follows the user's local midnight, not UTC midnight."""
    svc = UsableTimeService()
    # 2026-07-05 12:00 UTC. In UTC+11 that's 23:00 local → only ~60 min left in the local day.
    anchor = datetime(2026, 7, 5, 12, 0, tzinfo=timezone.utc)
    assert svc.calculate([], anchor=anchor, user_timezone="Pacific/Noumea") == 60
    # Same instant on UTC: 12h to UTC midnight → capped at the 4-hour max.
    assert svc.calculate([], anchor=anchor, user_timezone="UTC") == 240
    # Bad timezone string falls back to UTC without crashing.
    assert svc.calculate([], anchor=anchor, user_timezone="Not/AZone") == 240
