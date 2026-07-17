"""
Behavioral patterns from Apple Health + commutes, for the Insights screen (TIME-253).

Turns the raw time-series (WorkoutSession, HourlyActivity, confirmed CommuteEvents) into plain-language
"here's what we noticed about you" statements over a ~28-day window. Read-only; degrades to fewer/no
items when there isn't enough data (same discipline as LearnedPreferencesService). Each item is
{category, icon, title, detail}; the icon strings are SF Symbols the iOS surface renders directly.
"""
from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from statistics import mean
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.commute_repository import CommuteRepository
from app.repositories.hourly_activity_repository import HourlyActivityRepository
from app.repositories.workout_session_repository import WorkoutSessionRepository
from app.services.recommendation.time_service import part_of_day

WINDOW_DAYS = 28
_WEEKS = WINDOW_DAYS / 7
_GYM_TYPES = {"strength", "hiit", "functional"}
_SIT_STEP_THRESHOLD = 250        # an hour under this many steps counts as sedentary
_WAKING_START, _WAKING_END = 7, 23
_METERS_PER_MILE = 1609.344

_TOD_LABELS = {
    "early_morning": "early mornings",
    "morning": "mornings",
    "midday": "midday",
    "afternoon": "afternoons",
    "evening": "evenings",
    "night": "late evenings",
}


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _local_hour(dt: datetime, tz: str) -> int:
    try:
        return _utc(dt).astimezone(ZoneInfo(tz)).hour
    except Exception:
        return _utc(dt).hour


def _local_weekday(dt: datetime, tz: str) -> str:
    try:
        return _utc(dt).astimezone(ZoneInfo(tz)).strftime("%A")
    except Exception:
        return _utc(dt).strftime("%A")


def _modal_tod(times: list[datetime], tz: str) -> str:
    if not times:
        return "various times"
    counts = Counter(_TOD_LABELS[part_of_day(_local_hour(t, tz))] for t in times)
    return counts.most_common(1)[0][0]


def _modal_weekday(times: list[datetime], tz: str) -> str | None:
    if not times:
        return None
    counts = Counter(_local_weekday(t, tz) for t in times)
    day, n = counts.most_common(1)[0]
    return day if n >= 2 else None


class BehavioralPatternsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def for_user(self, user_id: uuid.UUID, user_timezone: str = "UTC") -> dict:
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=WINDOW_DAYS)
        patterns: list[dict] = []

        workouts = await WorkoutSessionRepository(self.db).list_in_range(user_id, start, now)
        patterns += self._running(workouts, user_timezone)
        patterns += self._gym(workouts, user_timezone)

        hourly = await HourlyActivityRepository(self.db).list_in_range(user_id, start, now)
        patterns += self._movement(hourly, user_timezone)

        minutes = await CommuteRepository(self.db).sum_confirmed_minutes_in_range(user_id, start, now)
        patterns += self._driving(minutes)

        return {"patterns": patterns, "based_on_days": WINDOW_DAYS}

    def _running(self, workouts, tz: str) -> list[dict]:
        runs = [w for w in workouts if w.workout_type == "running"]
        if len(runs) < 2:
            return []
        starts = [_utc(w.started_at) for w in runs]
        runs_per_week = round(len(runs) / _WEEKS, 1)
        avg_dur = round(mean(w.duration_minutes for w in runs))
        tod = _modal_tod(starts, tz)
        miles = sum((w.distance_meters or 0) for w in runs) / _METERS_PER_MILE
        if miles >= 0.5:
            miles_per_week = miles / _WEEKS
            detail = (f"About {miles_per_week:.1f} miles/week over ~{runs_per_week} runs, "
                      f"usually {tod}, ~{avg_dur} min each.")
        else:
            detail = f"About {runs_per_week} runs/week, usually {tod}, ~{avg_dur} min each."
        return [{"category": "workouts", "icon": "figure.run", "title": "Running", "detail": detail}]

    def _gym(self, workouts, tz: str) -> list[dict]:
        gym = [w for w in workouts if w.workout_type in _GYM_TYPES]
        if len(gym) < 2:
            return []
        per_week = round(len(gym) / _WEEKS, 1)
        weekday = _modal_weekday([_utc(w.started_at) for w in gym], tz)
        tod = _modal_tod([_utc(w.started_at) for w in gym], tz)
        on_day = f" on {weekday}s" if weekday else ""
        detail = f"About {per_week}×/week{on_day}, usually {tod}."
        return [{"category": "workouts", "icon": "figure.strengthtraining.traditional",
                 "title": "Gym", "detail": detail}]

    def _movement(self, hourly, tz: str) -> list[dict]:
        waking = [h for h in hourly if _WAKING_START <= _local_hour(h.hour_start, tz) < _WAKING_END]
        if len(waking) < 24:  # need a few days of waking-hour data
            return []
        sedentary = [h for h in waking if h.steps < _SIT_STEP_THRESHOLD]
        pct = round(100 * len(sedentary) / len(waking))
        tod = _modal_tod([_utc(h.hour_start) for h in sedentary], tz)
        streak = self._avg_sedentary_streak_hours(sedentary)
        streak_str = f", ~{streak}h at a stretch" if streak >= 2 else ""
        detail = f"You're sitting about {pct}% of your waking hours — most often in the {tod}{streak_str}."
        return [{"category": "movement", "icon": "figure.seated.side",
                 "title": "Sitting vs. moving", "detail": detail}]

    @staticmethod
    def _avg_sedentary_streak_hours(sedentary) -> int:
        hours = sorted(_utc(h.hour_start) for h in sedentary)
        if not hours:
            return 0
        streaks: list[int] = []
        run = 1
        for i in range(1, len(hours)):
            if (hours[i] - hours[i - 1]).total_seconds() == 3600:
                run += 1
            else:
                streaks.append(run)
                run = 1
        streaks.append(run)
        return round(mean(streaks))

    def _driving(self, total_minutes: int) -> list[dict]:
        if not total_minutes or total_minutes <= 0:
            return []
        per_day = round(total_minutes / WINDOW_DAYS)
        per_week_h = total_minutes / 60 / _WEEKS
        detail = f"About {per_day} min/day (~{per_week_h:.1f} h/week) on your work commute."
        return [{"category": "driving", "icon": "car.fill", "title": "Commute", "detail": detail}]
