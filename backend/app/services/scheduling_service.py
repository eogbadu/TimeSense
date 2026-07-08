"""
Scheduling core — finds free slots in the user's day and measures free time before a deadline,
within a working-hours window and around already-scheduled tasks. Shared by feasibility warnings
(TIME-084) and auto-placement (TIME-085).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence
from zoneinfo import ZoneInfo

# Default working window (local). Later configurable per user in Settings.
WORK_START_HOUR = 8
WORK_END_HOUR = 21


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class SchedulingService:
    def __init__(self, work_start_hour: int = WORK_START_HOUR, work_end_hour: int = WORK_END_HOUR):
        self.work_start_hour = work_start_hour
        self.work_end_hour = work_end_hour

    def _window(self, now: datetime, tz_name: str) -> tuple[datetime, datetime]:
        """Today's working window [start, end] in UTC."""
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = timezone.utc
        local = now.astimezone(tz)
        start = local.replace(hour=self.work_start_hour, minute=0, second=0, microsecond=0)
        end = local.replace(hour=self.work_end_hour, minute=0, second=0, microsecond=0)
        return start.astimezone(timezone.utc), end.astimezone(timezone.utc)

    def _busy(self, tasks: Sequence, lo: datetime, hi: datetime) -> list[tuple[datetime, datetime]]:
        """Merged busy blocks (scheduled tasks) clamped to [lo, hi]."""
        blocks: list[tuple[datetime, datetime]] = []
        for t in tasks:
            if t.scheduled_start is None or t.scheduled_end is None:
                continue
            s, e = _utc(t.scheduled_start), _utc(t.scheduled_end)
            if e <= lo or s >= hi:
                continue
            blocks.append((max(s, lo), min(e, hi)))
        blocks.sort()
        merged: list[tuple[datetime, datetime]] = []
        for s, e in blocks:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))
        return merged

    def _earliest_in_window(
        self, cursor: datetime, window_end: datetime, dur: timedelta, busy: Sequence
    ) -> datetime | None:
        """Earliest start in [cursor, window_end] where `dur` fits around the busy blocks."""
        if cursor + dur > window_end:
            return None
        for s, e in self._busy(busy, cursor, window_end):
            if s - cursor >= dur:
                return cursor
            cursor = max(cursor, e)
            if cursor + dur > window_end:
                return None
        return cursor if cursor + dur <= window_end else None

    def find_slot(
        self,
        now: datetime,
        duration_min: int,
        scheduled_tasks: Sequence,
        tz_name: str = "UTC",
        not_before: datetime | None = None,
    ) -> datetime | None:
        """Earliest start time today at which `duration_min` fits inside the working window and
        around scheduled tasks. None if it doesn't fit today."""
        window_start, window_end = self._window(now, tz_name)
        cursor = max(now, window_start)
        if not_before is not None:
            cursor = max(cursor, _utc(not_before))
        return self._earliest_in_window(
            cursor, window_end, timedelta(minutes=max(1, duration_min)), scheduled_tasks
        )

    def find_slot_multiday(
        self,
        now: datetime,
        duration_min: int,
        busy: Sequence,
        tz_name: str = "UTC",
        not_before: datetime | None = None,
        max_days: int = 3,
    ) -> datetime | None:
        """Earliest free slot across today and the next few days — rolls forward when today is full.
        `busy` may span multiple days (scheduled tasks + calendar events); each day's search is
        clamped to that day's working window."""
        dur = timedelta(minutes=max(1, duration_min))
        for offset in range(max(1, max_days)):
            anchor = now + timedelta(days=offset)
            window_start, window_end = self._window(anchor, tz_name)
            cursor = max(window_start, now) if offset == 0 else window_start
            if not_before is not None:
                cursor = max(cursor, _utc(not_before))
            if cursor >= window_end:
                continue
            slot = self._earliest_in_window(cursor, window_end, dur, busy)
            if slot is not None:
                return slot
        return None

    def free_minutes_before(
        self,
        deadline: datetime,
        now: datetime,
        scheduled_tasks: Sequence,
        tz_name: str = "UTC",
    ) -> int:
        """Unscheduled minutes between now and `deadline`, inside the working window."""
        window_start, window_end = self._window(now, tz_name)
        start = max(now, window_start)
        end = min(_utc(deadline), window_end)
        if end <= start:
            return 0
        free = int((end - start).total_seconds() / 60)
        for s, e in self._busy(scheduled_tasks, start, end):
            free -= int((min(e, end) - max(s, start)).total_seconds() / 60)
        return max(0, free)
