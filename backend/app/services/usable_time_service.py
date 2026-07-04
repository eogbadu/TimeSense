from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence

from app.models.task import Task


class UsableTimeService:
    """
    Calculates how many minutes of uninterrupted usable time the user has
    starting from `anchor` (defaults to now UTC).

    Algorithm:
      1. Collect all scheduled tasks that overlap or start after anchor.
      2. Merge overlapping/adjacent blocks into free windows.
      3. Return the size of the window that starts at (or contains) anchor,
         capped at MAX_WINDOW_MINUTES.

    "Usable" means: no scheduled task is blocking the time.
    End-of-day cap: we never return more than the minutes remaining until midnight UTC.
    """

    MAX_WINDOW_MINUTES: int = 240  # 4-hour cap — anything longer isn't meaningful for "right now"
    MIN_WINDOW_MINUTES: int = 5    # below this we report 0 rather than mislead

    def calculate(
        self,
        tasks: Sequence[Task],
        anchor: datetime | None = None,
    ) -> int:
        now = anchor or datetime.now(timezone.utc)

        # Minutes until midnight UTC (end-of-day cap)
        midnight = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=1)
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
