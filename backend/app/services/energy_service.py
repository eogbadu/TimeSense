"""Energy — modelled as a recovery budget that depletes over the day.

THE PROBLEM THIS REPLACES (TIME-288)

There were two different energy values that disagreed with each other:

  * the SCORER read `recommendation/context_builder._health`, which derived energy from sleep alone
    and hard-coded "medium" whenever there was no sleep sample — so activity never reached scoring
    at all;
  * the DISPLAY (Now card, Why sheet) read `recommendation_explainer._activity_energy`, where
    30+ minutes of exercise or 8000+ steps counted as HIGH energy.

The display rule is backwards. Being busy all day does not leave you with more capacity; it leaves
you with less. The reported symptom was TimeSense announcing "high energy" late in the evening after
a full day and recommending something demanding on the strength of it.

They also disagreed on vocabulary: the display said "moderate" where the engine's rank map expects
"medium". That would raise a KeyError; it only ever avoided one because the engine never saw the
display's value.

THE MODEL

Last night's sleep sets a morning budget. The day spends it:

  * hours awake — the largest and most reliable drain
  * effort already spent — exercise, meetings and deep work done today
  * a long sedentary stretch — sitting for hours is not restorative either, it is its own kind of
    depleting, so it is a (small) drain rather than the old rule's evidence of low energy
  * a circadian shape on top: an early-morning ramp, the post-lunch dip, and the evening decline

Nothing here is HealthKit-dependent. With no data at all the model still answers from time of day
and a typical wake time, which is strictly better than the old hard-coded "medium".
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.localtime import local_today, resolve_zone

LOW, MEDIUM, HIGH = "low", "medium", "high"

# The engine ranks required-vs-available energy with this map; anything outside it is a bug.
ENERGY_RANK: dict[str, int] = {LOW: 0, MEDIUM: 1, HIGH: 2}

# Copy reads better as "moderate" than "medium", but the engine must only ever see the canonical
# value. One place to translate, so the two can never drift apart again.
_DISPLAY_LABEL = {LOW: "low", MEDIUM: "moderate", HIGH: "high"}

# Score thresholds. Deliberately generous at the top: claiming "high energy" is an invitation to
# start something demanding, so it should require genuinely good conditions.
_HIGH_THRESHOLD = 0.66
_LOW_THRESHOLD = 0.36

# When we have no sleep data, assume an ordinary night rather than a good or bad one.
_DEFAULT_BUDGET = 0.72
# ...and if we don't know when they woke, assume a typical morning.
_ASSUMED_WAKE_HOUR = 7

# Drains, per unit. Tuned so a normal working day lands mid-range and a heavy one bottoms out.
_DRAIN_PER_HOUR_AWAKE = 0.030      # ~0.48 over a 16-hour day
_DRAIN_PER_EXERCISE_HOUR = 0.16
_DRAIN_PER_COMMITTED_HOUR = 0.05   # meetings / deep work already done today
_DRAIN_PER_10K_STEPS_OVER_BASELINE = 0.12
_STEP_BASELINE = 6000
_SEDENTARY_DRAIN = 0.09            # applied once past _SEDENTARY_MINUTES
_SEDENTARY_MINUTES = 240


@dataclass(frozen=True)
class EnergyInputs:
    """Everything the model reads. Kept separate from the DB so the maths is pure and testable."""

    local_hour: float                    # 0..24, fractional
    sleep_hours: float | None = None
    hours_awake: float | None = None     # from a real wake time when we have one
    exercise_minutes: int | None = None
    steps: int | None = None
    sedentary_minutes: int | None = None
    committed_minutes_today: int | None = None   # meetings / deep work already spent


@dataclass(frozen=True)
class EnergyEstimate:
    level: str                 # low | medium | high — the canonical value the engine uses
    score: float               # 0..1, for ordering and explanation
    sleep_hours: float | None
    sleep_quality: str | None  # poor | okay | good
    reason: str                # one plain-language sentence for the Why sheet
    source: str                # sleep | activity | time_of_day | checkin

    @property
    def display_label(self) -> str:
        return _DISPLAY_LABEL[self.level]


def sleep_budget(sleep_hours: float | None) -> tuple[float, str | None]:
    """How much the night gives you to spend. Returns (budget 0..1, quality)."""
    if sleep_hours is None:
        return _DEFAULT_BUDGET, None
    if sleep_hours >= 8:
        return 1.0, "good"
    if sleep_hours >= 7:
        return 0.88, "good"
    if sleep_hours >= 6:
        return 0.66, "okay"
    if sleep_hours >= 5:
        return 0.45, "poor"
    return 0.28, "poor"


def circadian_modifier(local_hour: float) -> float:
    """The shape of a day, independent of what you've done with it.

    Negative before you're properly awake, flat through the morning, a dip after lunch, a partial
    recovery, then a steady decline into the evening.
    """
    if local_hour < 5:
        return -0.45          # the middle of the night is not a working window
    if local_hour < 7:
        return -0.10          # still ramping up
    if local_hour < 12:
        return 0.05           # the best part of most people's day
    if local_hour < 13:
        return 0.0
    if local_hour < 15:
        return -0.06          # post-lunch dip
    if local_hour < 18:
        return -0.02          # second wind
    if local_hour < 21:
        return -0.12          # winding down
    return -0.25              # late


def compute_energy(inputs: EnergyInputs) -> EnergyEstimate:
    """The whole model, as a pure function."""
    budget, quality = sleep_budget(inputs.sleep_hours)

    hours_awake = inputs.hours_awake
    if hours_awake is None:
        # No wake sample: assume a typical morning. Never negative — before the assumed wake time
        # the user is simply up early, not "un-awake".
        hours_awake = max(0.0, inputs.local_hour - _ASSUMED_WAKE_HOUR)

    score = budget
    drains: list[tuple[str, float]] = []

    awake_drain = hours_awake * _DRAIN_PER_HOUR_AWAKE
    score -= awake_drain
    if hours_awake >= 10:
        drains.append(("a long day already", awake_drain))

    if inputs.exercise_minutes:
        drain = (inputs.exercise_minutes / 60) * _DRAIN_PER_EXERCISE_HOUR
        score -= drain
        if inputs.exercise_minutes >= 30:
            drains.append(("a workout today", drain))

    if inputs.committed_minutes_today:
        drain = (inputs.committed_minutes_today / 60) * _DRAIN_PER_COMMITTED_HOUR
        score -= drain
        if inputs.committed_minutes_today >= 180:
            drains.append(("a lot of committed time today", drain))

    if inputs.steps and inputs.steps > _STEP_BASELINE:
        drain = ((inputs.steps - _STEP_BASELINE) / 10000) * _DRAIN_PER_10K_STEPS_OVER_BASELINE
        score -= drain
        if inputs.steps >= 12000:
            drains.append(("a lot of moving around", drain))

    # Sitting for hours is not restorative — it is its own kind of depleting. The old rule read a
    # long sedentary stretch as EVIDENCE of low energy; here it is a (small) cause of it.
    if inputs.sedentary_minutes and inputs.sedentary_minutes >= _SEDENTARY_MINUTES:
        score -= _SEDENTARY_DRAIN
        drains.append(("a long stretch sitting", _SEDENTARY_DRAIN))

    score += circadian_modifier(inputs.local_hour)
    score = max(0.0, min(1.0, score))

    # Without a sleep sample we are guessing from the clock, and "high energy" is an invitation to
    # start something demanding. Don't make that claim on no evidence — cap at medium and let a
    # connected Health account earn the top band.
    if inputs.sleep_hours is None:
        score = min(score, _HIGH_THRESHOLD - 0.01)

    level = HIGH if score >= _HIGH_THRESHOLD else (LOW if score <= _LOW_THRESHOLD else MEDIUM)

    source = "sleep" if inputs.sleep_hours is not None else (
        "activity" if (inputs.steps or inputs.exercise_minutes) else "time_of_day"
    )
    return EnergyEstimate(
        level=level,
        score=round(score, 3),
        sleep_hours=inputs.sleep_hours,
        sleep_quality=quality,
        reason=_reason(level, inputs, quality, drains),
        source=source,
    )


def _reason(level, inputs: EnergyInputs, quality: str | None,
            drains: list[tuple[str, float]]) -> str:
    """One honest sentence. Names the biggest reason rather than reciting every input."""
    parts: list[str] = []
    if inputs.sleep_hours is not None:
        parts.append(f"{inputs.sleep_hours:g}h sleep")
    biggest = max(drains, key=lambda d: d[1])[0] if drains else None
    if biggest:
        parts.append(biggest)

    if level == HIGH:
        lead = "Good capacity right now"
    elif level == LOW:
        lead = "Running low right now"
    else:
        lead = "Moderate capacity right now"

    if not parts:
        return f"{lead} — based on the time of day."
    return f"{lead} — {' and '.join(parts)}."


class EnergyService:
    """The single source of energy for the scorer, the Now cards and the Why sheet.

    Before TIME-288 those read two different implementations that disagreed on both the value and
    the vocabulary. Anything that needs energy should call this.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def estimate(
        self,
        user_id: uuid.UUID,
        now: datetime | None = None,
        user_timezone: str | None = None,
        committed_minutes_today: int | None = None,
    ) -> EnergyEstimate:
        from app.repositories.daily_activity_repository import DailyActivityRepository
        from app.repositories.sleep_wake_repository import SleepWakeRepository

        now = now or datetime.now(timezone.utc)
        zone = resolve_zone(user_timezone)
        local = now.astimezone(zone)
        today: date = local_today(user_timezone, now)

        sleep_hours: float | None = None
        hours_awake: float | None = None
        event = await SleepWakeRepository(self.db).get_latest_today(
            user_id, user_timezone=user_timezone
        )
        if event is not None:
            wake = _utc(event.wake_time)
            hours_awake = max(0.0, (now - wake).total_seconds() / 3600)
            if event.sleep_start is not None:
                sleep_hours = round((wake - _utc(event.sleep_start)).total_seconds() / 3600, 1)

        activity = await DailyActivityRepository(self.db).get_for_day(user_id, today)

        if committed_minutes_today is None:
            committed_minutes_today = await self._committed_minutes(user_id, today, now,
                                                                    user_timezone)

        return compute_energy(
            EnergyInputs(
                local_hour=local.hour + local.minute / 60,
                sleep_hours=sleep_hours,
                hours_awake=hours_awake,
                exercise_minutes=activity.exercise_minutes if activity else None,
                steps=activity.steps if activity else None,
                sedentary_minutes=activity.inactive_minutes if activity else None,
                committed_minutes_today=committed_minutes_today,
            )
        )

    async def _committed_minutes(
        self, user_id: uuid.UUID, today: date, now: datetime, user_timezone: str | None
    ) -> int:
        """Minutes of meetings and scheduled work already SPENT today.

        Only blocks that have already finished count — time still ahead of the user hasn't cost them
        anything yet. This is what makes a back-to-back morning show up as depletion by mid-
        afternoon, which a sleep-only reading could never express.
        """
        from app.core.localtime import local_day_bounds
        from app.repositories.synced_calendar_event_repository import (
            SyncedCalendarEventRepository,
        )
        from app.repositories.task_repository import TaskRepository

        day_start, day_end = local_day_bounds(today, user_timezone)
        minutes = 0

        for event in await SyncedCalendarEventRepository(self.db).list_window(
            user_id, day_start, day_end
        ):
            if event.all_day or event.starts_at is None or event.ends_at is None:
                continue
            if _utc(event.ends_at) <= now:
                minutes += int((_utc(event.ends_at) - _utc(event.starts_at)).total_seconds() / 60)

        for task in await TaskRepository(self.db).list_by_user(
            user_id=user_id, for_date=today, limit=200, user_timezone=user_timezone
        ):
            if task.scheduled_start is None or task.scheduled_end is None:
                continue
            # Skip calendar-sourced tasks — the meeting they mirror is already counted above.
            if task.source == "calendar":
                continue
            if _utc(task.scheduled_end) <= now:
                minutes += int(
                    (_utc(task.scheduled_end) - _utc(task.scheduled_start)).total_seconds() / 60
                )

        return max(0, minutes)


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
