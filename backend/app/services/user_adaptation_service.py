"""Derives what TimeSense has learned about one person, from the raw event history.

This is the answer to "how is TimeSense learning my habits, and how does that make it better?".
Before TIME-292 the answer was thin: a duration average, an acceptance rate keyed on action type,
and two read-only screens that fed nothing back. Everything else was recomputed live per request
over 28- or 30-day windows — too expensive to consult on every recommendation, which is precisely
why the scorer didn't consult it.

Design rules that matter more than the specific metrics:

  * Null, not zero, below a sample floor. "No evidence" and "evidence of nothing" are different
    claims, and conflating them is how a brand-new user ends up scored on noise.
  * Bucket in the USER'S timezone. An hour-of-day profile computed in UTC is meaningless for
    anyone who isn't in London, and silently re-buckets when they travel.
  * Derived, never authoritative. Every value here can be recomputed from the raw tables; nothing
    is lost if this is dropped and rebuilt.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.localtime import resolve_zone, user_timezone_of
from app.models.energy_checkin import EnergyCheckIn
from app.models.recommendation_event import RecommendationEvent
from app.models.sleep_wake import SleepWakeEvent
from app.models.task import Task
from app.models.task_duration_observation import TaskDurationObservation
from app.repositories.user_adaptation_repository import UserAdaptationRepository
from app.repositories.user_repository import UserRepository
from app.services.energy_service import ENERGY_RANK
from app.services.task_library import get_type

# How far back to look. Long enough to cover a few weeks of routine, short enough that a habit the
# user has genuinely changed stops being held against them.
WINDOW = timedelta(days=42)

# Minimum observations before a bucket is reported at all. Below this the value stays absent, so
# consumers stay neutral rather than acting on one or two data points.
MIN_SAMPLES_PER_BUCKET = 3
MIN_SAMPLES_OVERALL = 5

POSITIVE_OUTCOMES = frozenset({"agree", "done"})
NEGATIVE_OUTCOMES = frozenset({"disagree", "not_now", "snooze"})


def _rate(counts: dict[str, list[int]]) -> dict[str, float] | None:
    """{key: [positive, total]} -> {key: rate}, dropping under-evidenced buckets."""
    out = {
        key: round(pos / total, 3)
        for key, (pos, total) in counts.items()
        if total >= MIN_SAMPLES_PER_BUCKET
    }
    return out or None


class UserAdaptationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def rebuild(
        self, user_id: uuid.UUID, now: datetime | None = None
    ):
        now = now or datetime.now(timezone.utc)
        since = now - WINDOW

        user = await UserRepository(self.db).get_by_id(user_id)
        tz_name = user_timezone_of(user) if user is not None else "UTC"
        zone = resolve_zone(tz_name)

        completion_by_hour, completion_by_weekday, first_minutes, wind_down_minutes = \
            await self._task_rhythm(user_id, since, zone)
        acceptance_by_category, acceptance_by_action_type = \
            await self._acceptance(user_id, since)
        estimate_ratio_by_type = await self._estimate_accuracy(user_id, since)
        completions_by_energy = await self._completions_by_energy(user_id, since)
        energy_bias = await self._energy_bias(user_id, since)
        typical_wake = await self._typical_wake(user_id, since, zone)

        return await UserAdaptationRepository(self.db).upsert(
            user_id,
            computed_at=now,
            days_observed=WINDOW.days,
            completion_by_hour=completion_by_hour,
            completion_by_weekday=completion_by_weekday,
            acceptance_by_category=acceptance_by_category,
            acceptance_by_action_type=acceptance_by_action_type,
            estimate_ratio_by_type=estimate_ratio_by_type,
            completions_by_energy=completions_by_energy,
            energy_bias=energy_bias,
            typical_wake_minute=typical_wake,
            typical_first_task_minute=_median(first_minutes),
            typical_wind_down_minute=_median(wind_down_minutes),
            timezone=tz_name,
        )

    async def _task_rhythm(self, user_id, since, zone):
        """Completion rate by local hour and weekday, plus when the day tends to start and end.

        A task counts toward the hour it was SCHEDULED for — that is the question the engine asks
        ("is this a good hour to suggest work?"), not the hour it happened to be ticked off.
        """
        rows = (await self.db.execute(
            select(Task).where(Task.user_id == user_id, Task.created_at >= since)
        )).scalars().all()

        by_hour: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        by_weekday: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        first_minutes: list[int] = []
        wind_down_minutes: list[int] = []
        day_first: dict[str, int] = {}
        day_last: dict[str, int] = {}

        for task in rows:
            anchor = task.scheduled_start or task.due_at
            if anchor is None:
                continue
            local = _utc(anchor).astimezone(zone)
            done = task.status == "done"
            hour, weekday = str(local.hour), str(local.weekday())
            by_hour[hour][1] += 1
            by_weekday[weekday][1] += 1
            if done:
                by_hour[hour][0] += 1
                by_weekday[weekday][0] += 1
                minute = local.hour * 60 + local.minute
                key = local.date().isoformat()
                day_first[key] = min(day_first.get(key, minute), minute)
                day_last[key] = max(day_last.get(key, minute), minute)

        first_minutes = list(day_first.values())
        wind_down_minutes = list(day_last.values())
        return _rate(by_hour), _rate(by_weekday), first_minutes, wind_down_minutes

    async def _acceptance(self, user_id, since):
        """Acceptance by task category and by action type.

        Category is the addition that matters: the pre-existing learning was keyed on action_type
        alone, which is far coarser than what a user actually rejects — "not this errand" and "not
        this deep work" are different statements about the same action type.
        """
        rows = (await self.db.execute(
            select(RecommendationEvent).where(
                RecommendationEvent.user_id == user_id,
                RecommendationEvent.created_at >= since,
                RecommendationEvent.outcome.is_not(None),
            )
        )).scalars().all()

        by_action: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        by_category: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        task_types = await self._task_types_for_events(rows)

        for event in rows:
            if event.outcome not in POSITIVE_OUTCOMES | NEGATIVE_OUTCOMES:
                continue
            positive = 1 if event.outcome in POSITIVE_OUTCOMES else 0
            if event.action_type:
                by_action[event.action_type][1] += 1
                by_action[event.action_type][0] += positive
            category = task_types.get(event.id)
            if category:
                by_category[category][1] += 1
                by_category[category][0] += positive

        return _rate(by_category), _rate(by_action)

    async def _task_types_for_events(self, events) -> dict:
        """Map each impression to the CATEGORY of the task it was about."""
        task_ids = {e.task_id for e in events if getattr(e, "task_id", None)}
        if not task_ids:
            return {}
        rows = (await self.db.execute(
            select(Task.id, Task.task_type, Task.title).where(Task.id.in_(task_ids))
        )).all()
        by_task = {
            row[0]: get_type(row[1]).category for row in rows
        }
        return {
            e.id: by_task.get(e.task_id)
            for e in events if getattr(e, "task_id", None) in by_task
        }

    async def _estimate_accuracy(self, user_id, since) -> dict[str, float] | None:
        """actual / predicted per task type. >1 means we systematically under-estimate."""
        rows = (await self.db.execute(
            select(TaskDurationObservation).where(
                TaskDurationObservation.user_id == user_id,
                TaskDurationObservation.observed_at >= since,
                TaskDurationObservation.estimated_minutes.is_not(None),
            )
        )).scalars().all()

        ratios: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            if not row.estimated_minutes:
                continue
            ratios[row.task_type].append(row.actual_minutes / row.estimated_minutes)

        out = {
            key: round(sum(values) / len(values), 3)
            for key, values in ratios.items()
            if len(values) >= MIN_SAMPLES_PER_BUCKET
        }
        return out or None

    async def _completions_by_energy(self, user_id, since) -> dict[str, int] | None:
        """What energy level the user was at when work actually got finished.

        Feeds the per-user difficulty mapping in TIME-290: someone who reliably completes demanding
        work in the evening shouldn't be told the evening is wrong for them.
        """
        rows = (await self.db.execute(
            select(RecommendationEvent).where(
                RecommendationEvent.user_id == user_id,
                RecommendationEvent.created_at >= since,
                RecommendationEvent.outcome.in_(list(POSITIVE_OUTCOMES)),
            )
        )).scalars().all()

        counts: dict[str, int] = defaultdict(int)
        for event in rows:
            explanation = event.explanation or {}
            level = explanation.get("energy") if isinstance(explanation, dict) else None
            if level in ENERGY_RANK:
                counts[level] += 1
        total = sum(counts.values())
        return dict(counts) if total >= MIN_SAMPLES_OVERALL else None

    async def _energy_bias(self, user_id, since) -> float | None:
        """Signed mean of (reported rank - inferred rank) over the user's own check-ins.

        Negative means we consistently claim more capacity than they report having. This is the only
        real feedback the energy model has (TIME-289); it is COLLECTED and reported here, and
        deliberately not yet applied — a curve tuned on a handful of points bakes in noise.
        """
        rows = (await self.db.execute(
            select(EnergyCheckIn).where(
                EnergyCheckIn.user_id == user_id,
                EnergyCheckIn.reported_at >= since,
                EnergyCheckIn.inferred.is_not(None),
            )
        )).scalars().all()

        deltas = [
            ENERGY_RANK[r.reported] - ENERGY_RANK[r.inferred]
            for r in rows
            if r.reported in ENERGY_RANK and r.inferred in ENERGY_RANK
        ]
        if len(deltas) < MIN_SAMPLES_OVERALL:
            return None
        return round(sum(deltas) / len(deltas), 3)

    async def _typical_wake(self, user_id, since, zone) -> int | None:
        rows = (await self.db.execute(
            select(SleepWakeEvent).where(
                SleepWakeEvent.user_id == user_id,
                SleepWakeEvent.wake_time >= since,
            )
        )).scalars().all()
        minutes = []
        for row in rows:
            local = _utc(row.wake_time).astimezone(zone)
            minutes.append(local.hour * 60 + local.minute)
        return _median(minutes)


def _median(values: list[int]) -> int | None:
    """Median, not mean — one 3am night shouldn't move someone's typical wake time."""
    if len(values) < MIN_SAMPLES_OVERALL:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return int((ordered[mid - 1] + ordered[mid]) / 2)


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
