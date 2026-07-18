from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from app.models.task import Task


class UsableTimeService:
    """
    Calculates how many minutes of uninterrupted usable time the user has
    starting from `anchor` (defaults to now UTC).

    Algorithm:
      1. Collect all scheduled tasks — and any calendar events — that overlap or start after anchor.
      2. Merge overlapping/adjacent blocks into free windows.
      3. Return the size of the window that starts at (or contains) anchor,
         capped at MAX_WINDOW_MINUTES.

    "Usable" means: no scheduled task AND no calendar meeting is blocking the time. Overlapping
    task/event blocks merge, so an imported meeting that also exists as a Task isn't double-counted.
    End-of-day cap: we never return more than the minutes remaining until the user's *local*
    midnight (so "time left today" reflects the user's day, not the UTC day).
    """

    MAX_WINDOW_MINUTES: int = 240  # 4-hour cap — anything longer isn't meaningful for "right now"
    MIN_WINDOW_MINUTES: int = 5    # below this we report 0 rather than mislead

    def calculate(
        self,
        tasks: Sequence[Task],
        anchor: datetime | None = None,
        user_timezone: str = "UTC",
        events: Sequence[Any] | None = None,
    ) -> int:
        now = anchor or datetime.now(timezone.utc)

        # End-of-day cap = the user's next *local* midnight (converted to UTC), not UTC midnight —
        # otherwise "time left today" is wrong for anyone not on UTC.
        try:
            tz = ZoneInfo(user_timezone)
        except Exception:
            tz = timezone.utc
        local_now = now.astimezone(tz)
        midnight = datetime.combine(local_now.date() + timedelta(days=1), time(0, 0), tzinfo=tz).astimezone(timezone.utc)
        minutes_to_midnight = int((midnight - now).total_seconds() / 60)

        # Collect blocks that start before midnight and have a scheduled_end
        blocks: list[tuple[datetime, datetime]] = []
        for task in tasks:
            if task.scheduled_start is None or task.scheduled_end is None:
                continue
            start = _utc(task.scheduled_start)
            end = _utc(task.scheduled_end)
            if end <= now or start >= midnight:
                continue
            # Clamp to [now, midnight]
            blocks.append((max(start, now), min(end, midnight)))

        # Calendar meetings block time too. Skip all-day events (they don't consume a working slot);
        # overlapping task/event blocks merge below, so no double-count with an imported meeting.
        for event in events or []:
            if getattr(event, "all_day", False):
                continue
            start = _utc(event.starts_at)
            end = _utc(event.ends_at)
            if end <= now or start >= midnight:
                continue
            blocks.append((max(start, now), min(end, midnight)))

        if not blocks:
            return min(minutes_to_midnight, self.MAX_WINDOW_MINUTES)

        # Sort and merge overlapping/adjacent blocks
        blocks.sort()
        merged: list[tuple[datetime, datetime]] = [blocks[0]]
        for start, end in blocks[1:]:
            prev_start, prev_end = merged[-1]
            if start <= prev_end:
                merged[-1] = (prev_start, max(prev_end, end))
            else:
                merged.append((start, end))

        # The usable window starts at `now` and ends at the first block's start,
        # OR if a block already contains `now`, there's no free time.
        first_start, first_end = merged[0]
        if first_start <= now:
            # Already in a scheduled block — usable time starts after it ends
            free_start = first_end
            # Find the next gap after the block
            if len(merged) > 1:
                gap_minutes = int((merged[1][0] - free_start).total_seconds() / 60)
            else:
                gap_minutes = int((midnight - free_start).total_seconds() / 60)
        else:
            gap_minutes = int((first_start - now).total_seconds() / 60)

        if gap_minutes < self.MIN_WINDOW_MINUTES:
            return 0
        return min(gap_minutes, self.MAX_WINDOW_MINUTES, minutes_to_midnight)


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
