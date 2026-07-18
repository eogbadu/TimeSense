"""
Chart-ready time series for the Insights screen (TIME-273).

Turns the raw HealthKit tables (DailyActivity, WorkoutSession, HourlyActivity) into small,
read-only numeric series the iOS Swift Charts surface plots directly — daily steps/exercise,
weekly running mileage, and an average-steps-by-hour profile for sit-vs-move. All boundaries and
hour bucketing use the user's timezone. Degrades to empty series when there isn't enough data.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.daily_activity_repository import DailyActivityRepository
from app.repositories.hourly_activity_repository import HourlyActivityRepository
from app.repositories.workout_session_repository import WorkoutSessionRepository

_METERS_PER_MILE = 1609.344
_RUNNING_TYPES = frozenset({"running", "run"})


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _tz(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("UTC")


def _week_start(d: date) -> date:
    """Monday of the week containing d."""
    return d - timedelta(days=d.weekday())


class InsightsSeriesService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def daily_activity(
        self, user_id: uuid.UUID, days: int, user_timezone: str = "UTC"
    ) -> list[dict]:
        """One point per day that has data: {day, steps, exercise_minutes}."""
        today = datetime.now(_tz(user_timezone)).date()
        start = today - timedelta(days=days - 1)
        rows = await DailyActivityRepository(self.db).list_in_range(user_id, start, today)
        return [
            {"day": r.day, "steps": r.steps, "exercise_minutes": r.exercise_minutes or 0}
            for r in rows
        ]

    async def weekly_workouts(
        self, user_id: uuid.UUID, weeks: int, user_timezone: str = "UTC"
    ) -> list[dict]:
        """One point per calendar week (Mon-anchored): running miles + run count + total workouts.

        Weeks with no workouts are included as zeros so the chart shows a continuous timeline.
        """
        tz = _tz(user_timezone)
        today = datetime.now(tz).date()
        first_week = _week_start(today) - timedelta(weeks=weeks - 1)
        start_dt = datetime.combine(first_week, datetime.min.time(), tzinfo=tz).astimezone(timezone.utc)
        now = datetime.now(timezone.utc)

        workouts = await WorkoutSessionRepository(self.db).list_in_range(user_id, start_dt, now)

        buckets: dict[date, dict] = {
            first_week + timedelta(weeks=i): {"running_miles": 0.0, "running_count": 0, "total_count": 0}
            for i in range(weeks)
        }
        for w in workouts:
            local_day = _utc(w.started_at).astimezone(tz).date()
            wk = _week_start(local_day)
            b = buckets.get(wk)
            if b is None:
                continue
            b["total_count"] += 1
            if w.workout_type in _RUNNING_TYPES:
                b["running_count"] += 1
                b["running_miles"] += (w.distance_meters or 0) / _METERS_PER_MILE

        return [
            {
                "week_start": wk,
                "running_miles": round(b["running_miles"], 2),
                "running_count": b["running_count"],
                "total_count": b["total_count"],
            }
            for wk, b in sorted(buckets.items())
        ]

    async def hourly_steps(
        self, user_id: uuid.UUID, days: int, user_timezone: str = "UTC"
    ) -> list[dict]:
        """Average steps for each hour-of-day (0-23) over the window — the sit-vs-move profile.

        Averaged across the number of distinct local days that actually reported any data, so a
        partial window doesn't understate the typical hour.
        """
        tz = _tz(user_timezone)
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days)
        rows = await HourlyActivityRepository(self.db).list_in_range(user_id, start, now)

        totals = [0] * 24
        active_days: set[date] = set()
        for r in rows:
            local = _utc(r.hour_start).astimezone(tz)
            totals[local.hour] += r.steps
            active_days.add(local.date())

        divisor = max(len(active_days), 1)
        return [{"hour": h, "avg_steps": round(totals[h] / divisor)} for h in range(24)]
