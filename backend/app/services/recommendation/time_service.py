"""Centralized time service. All current-time logic in the engine goes through here — never scatter
``datetime.now()`` across candidate generators. Timezone-aware and testable via an injected ``now``."""

from __future__ import annotations

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from app.services.recommendation.types import PartOfDay, TimeSnapshot

_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _zone(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("UTC")


def part_of_day(hour: int) -> PartOfDay:
    if 5 <= hour < 8:
        return "early_morning"
    if 8 <= hour < 11:
        return "morning"
    if 11 <= hour < 14:
        return "midday"
    if 14 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def get_time_snapshot(
    tz_name: str,
    now: datetime | None = None,
    work_start: time = time(9, 0),
    work_end: time = time(17, 0),
) -> TimeSnapshot:
    """Return a timezone-aware snapshot of "now". ``now`` is optional for deterministic tests."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now_utc = now.astimezone(timezone.utc)
    local = now.astimezone(_zone(tz_name))

    is_weekend = local.weekday() >= 5
    is_work_hours = (not is_weekend) and (work_start <= local.time() < work_end)

    return TimeSnapshot(
        now=now_utc.isoformat(),
        timezone=tz_name,
        local_time=local.isoformat(),
        day_of_week=_DAYS[local.weekday()],
        part_of_day=part_of_day(local.hour),
        is_weekend=is_weekend,
        is_work_hours=is_work_hours,
        hour=local.hour,
    )


def minutes_between(earlier: datetime, later: datetime) -> int:
    """Whole minutes from ``earlier`` to ``later`` (negative if later precedes earlier)."""
    a = earlier if earlier.tzinfo else earlier.replace(tzinfo=timezone.utc)
    b = later if later.tzinfo else later.replace(tzinfo=timezone.utc)
    return int((b - a).total_seconds() // 60)
