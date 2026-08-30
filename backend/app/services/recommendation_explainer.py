"""
Recommendation explanation pipeline (the rich "Why This Recommendation?").

Given the chosen task, the alternatives, and the user's live context, produce a structured
explanation: the context used, deterministic decision factors, a confidence score, why each
alternative wasn't picked, and a one-paragraph summary (LLM, with a deterministic fallback).

Signals are included only when we actually have them — calendar/time/task always; health/energy only
if there's a sleep signal; location only if there's a recent commute. We never fabricate context.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Sequence
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commute import CommuteEvent
from app.models.sleep_wake import SleepWakeEvent
from app.services.energy_service import EnergyService
from app.repositories.synced_calendar_event_repository import SyncedCalendarEventRepository
from app.repositories.task_repository import TaskRepository
from app.services.recommendation.scoring.score import score_to_confidence
from app.services.scheduling_service import SchedulingService

_SUMMARY_SYSTEM = (
    "You are a calm personal time assistant. In 2–3 sentences, summarise why the chosen task is the "
    "best thing to do now, grounded ONLY in the provided context (time, calendar, energy, location, "
    "task). The task is already chosen — justify it, never suggest resting or a different task. "
    "Speak to 'you'. No preamble, no lists."
)


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _local(now: datetime, tz_name: str) -> datetime:
    try:
        return now.astimezone(ZoneInfo(tz_name))
    except Exception:
        return now


def _priority_label(p: int) -> str:
    return "High" if p <= 2 else ("Medium" if p == 3 else "Low")


def _time_of_day(local_now: datetime) -> tuple[str, str]:
    h = local_now.hour
    if 5 <= h < 11:
        return "morning", "a strong focus window"
    if 11 <= h < 14:
        return "midday", "a steady window"
    if 14 <= h < 17:
        return "afternoon", "a decent window, though focus can dip after lunch"
    if 17 <= h < 21:
        return "evening", "a wind-down window, better for lighter tasks"
    return "late", "a low-focus window"


async def _health(db: AsyncSession, user_id, now: datetime, tz_name: str):
    """Energy signal for the Why screen.

    Delegates to EnergyService so the sheet and the scorer can never again disagree. They used to:
    this module computed energy from ACTIVITY, where 30+ minutes of exercise or 8000+ steps read as
    "high" — so a busy day announced high energy in the evening — while the engine used sleep alone
    and hard-coded "medium" without a sample. They also used different vocabularies ("moderate" here
    vs "medium" there), which would have raised a KeyError had the value ever reached the ranker
    (TIME-288).

    Returns {energy, wake, sleep_hours, steps, source, reason} or None when there is nothing to say.
    """
    today = _local(now, tz_name).date()
    estimate = await EnergyService(db).estimate(user_id, now=now, user_timezone=tz_name)

    wake_label = None
    rows = (await db.execute(
        select(SleepWakeEvent)
        .where(SleepWakeEvent.user_id == user_id)
        .order_by(SleepWakeEvent.wake_time.desc())
        .limit(1)
    )).scalars().all()
    if rows:
        wake_local = _local(_utc(rows[0].wake_time), tz_name)
        if wake_local.date() == today:
            wake_label = wake_local.strftime("%-I:%M %p")

    from app.repositories.daily_activity_repository import DailyActivityRepository
    activity = await DailyActivityRepository(db).get_for_day(user_id, today)

    # With no health data at all the estimate is time-of-day only; say nothing rather than present
    # a clock reading as a health signal.
    if wake_label is None and activity is None and estimate.sleep_hours is None:
        return None

    return {
        # `energy` keeps the human-facing wording the sheet already used; the canonical level the
        # engine ranks on is `level`. One translation point, so they cannot drift apart again.
        "energy": estimate.display_label,
        "level": estimate.level,
        "wake": wake_label,
        "sleep_hours": estimate.sleep_hours,
        "steps": activity.steps if activity is not None else None,
        "source": estimate.source,
        "reason": estimate.reason,
    }


async def _current_place(db: AsyncSession, user_id, now: datetime):
    """The user's current derived place from the app (UserLocationState) — a row with place_name
    (None = out and about) and is_home, or None if we have no recent signal."""
    from app.repositories.user_location_repository import UserLocationRepository
    return await UserLocationRepository(db).get_current(user_id, now)


async def _location(db: AsyncSession, user_id, now: datetime):
    """(Legacy) commute-derived location, kept for reference."""
    rows = (await db.execute(
        select(CommuteEvent)
        .where(CommuteEvent.user_id == user_id)
        .order_by(CommuteEvent.detected_end.desc())
        .limit(1)
    )).scalars().all()
    if not rows:
        return None
    ev = rows[0]
    start, end = _utc(ev.detected_start), _utc(ev.detected_end)
    if start - timedelta(minutes=15) <= now <= end + timedelta(minutes=15):
        return "commuting"
    if end.date() == now.date():
        return "settled"
    return None


async def _free_and_next(db, user, today_tasks: Sequence, now: datetime, tz_name: str):
    """Real free time until the next commitment, or the end of the working day — accounting for BOTH
    scheduled tasks AND the user's calendar events, inside working hours.

    Returns (free_minutes, next_event_label | None, off_hours). `free_minutes` is time the user can
    start using NOW, so it is 0 outside the working window — including the hours BEFORE it opens,
    which used to report the entire day ahead as though it were available (TIME-308). `off_hours`
    lets the copy say why the number is 0 instead of implying the day is full."""
    prefs = user.preferences
    sched = SchedulingService(
        work_start_hour=prefs.work_start_hour if prefs else 8,
        work_end_hour=prefs.work_end_hour if prefs else 21,
    )
    _, window_end = sched._window(now, tz_name)

    # Search the whole local day for the next commitment (so evening tasks/events count too), but keep
    # the free-time fallback at end-of-workday.
    try:
        local_now = now.astimezone(ZoneInfo(tz_name))
        day_end = local_now.replace(hour=23, minute=59, second=59, microsecond=0).astimezone(timezone.utc)
    except Exception:
        day_end = now.replace(hour=23, minute=59, second=59, microsecond=0)

    events = await SyncedCalendarEventRepository(db).list_window(user.id, now, day_end)
    commitments = await TaskRepository(db).upcoming_commitments(user.id, now, day_end)

    # Busy blocks = scheduled tasks + timed calendar events.
    busy: list = [t for t in today_tasks if t.scheduled_start and t.scheduled_end]
    busy += [
        SimpleNamespace(scheduled_start=e.starts_at, scheduled_end=e.ends_at)
        for e in events if not e.all_day
    ]

    # The next commitment (task or meeting) after now — a task's scheduled time, else its due time
    # (so a due-only email/Notion/manual task is named), plus timed calendar events.
    starts: list[tuple[datetime, str]] = []
    for t in commitments:
        when: datetime | None = None
        if t.scheduled_start:
            s = _utc(t.scheduled_start)
            if now < s <= day_end:
                when = s
        if when is None and t.due_at:
            d = _utc(t.due_at)
            if now < d <= day_end:
                when = d
        if when is not None:
            starts.append((when, t.title))
    for e in events:
        if not e.all_day:
            s = _utc(e.starts_at)
            if now < s <= day_end:
                starts.append((s, e.title))

    if starts:
        next_start, next_title = min(starts, key=lambda x: x[0])
        free = sched.free_minutes_available_now(next_start, now, busy, tz_name)
        label = f"{next_title} at {_local(next_start, tz_name).strftime('%-I:%M %p')}"
    else:
        free = sched.free_minutes_available_now(window_end, now, busy, tz_name)
        label = None
    return free, label, not sched.within_working_hours(now, tz_name)


async def build_explanation(
    db: AsyncSession,
    user,
    best,
    alternatives: Sequence,
    today_tasks: Sequence,
    now: datetime,
    tz_name: str,
    gateway,
    score: float = 0.0,
    alt_scores: dict[str, float] | None = None,
) -> dict:
    free_minutes, next_event, off_hours = await _free_and_next(db, user, today_tasks, now, tz_name)
    local_now = _local(now, tz_name)
    tod_label, tod_note = _time_of_day(local_now)
    health = await _health(db, user.id, now, tz_name)
    place = await _current_place(db, user.id, now)

    est = best.estimated_minutes or 0
    fits = est <= free_minutes if est else True

    # If the task itself is scheduled for a future time (e.g. an imported calendar event), lead with
    # that instead of a generic "free before your next meeting" line — otherwise the reasoning reads
    # nonsensically (e.g. a 4pm appointment explained by the free time before an 11am meeting).
    task_start = _utc(best.scheduled_start) if getattr(best, "scheduled_start", None) else None
    scheduled_at_label = (
        _local(task_start, tz_name).strftime("%-I:%M %p") if task_start and task_start > now else None
    )

    # ---- Context used (human bullets, only what we actually know) ----
    context_used: list[str] = []
    if scheduled_at_label:
        context_used.append(f"Calendar: this is scheduled for {scheduled_at_label}.")
    elif off_hours:
        context_used.append("Calendar: you're outside your working hours right now.")
    elif next_event:
        context_used.append(f"Calendar: {free_minutes} minutes free before {next_event}.")
    else:
        context_used.append(f"Calendar: {free_minutes} minutes free before your workday ends.")
    context_used.append(f"Time of day: it's {tod_label} — {tod_note}.")
    if place is not None:
        if place.place_name:
            context_used.append(f"Location: you're currently at {place.place_name}.")
        else:
            context_used.append("Location: you're out and about right now.")
    if health:
        # Say WHY, using the estimate's own reason. The old copy claimed energy was "based on
        # today's activity", which is no longer true and was backwards when it was: activity spends
        # capacity, it doesn't create it (TIME-288).
        woke = f" You woke at {health['wake']}." if health.get("wake") else ""
        context_used.append(f"Energy: {health['reason']}{woke}")
    if est:
        context_used.append(
            f"Task: {_priority_label(best.priority).lower()} priority, ~{est} min — "
            + (
                "outside your working hours."
                if off_hours
                else ("fits the time you have." if fits else "longer than the time you have right now.")
            )
        )

    # ---- Decision factors (deterministic ratings) ----
    factors = [{"name": "Priority", "rating": _priority_label(best.priority)}]
    if est:
        factors.append({"name": "Time fit", "rating": "Strong" if fits else ("Partial" if est <= free_minutes * 1.5 else "Tight")})
    if health:
        factors.append({"name": "Energy match", "rating": "Good" if health["energy"] in ("high", "moderate") else "Low"})
    if place is not None:
        factors.append({"name": "Location fit", "rating": "Good"})
    # Urgency from deadline
    if best.due_at is not None:
        due = _utc(best.due_at)
        if due < now:
            urg = "High"
        elif due.date() == now.date():
            urg = "Medium"
        else:
            urg = "Low"
    else:
        urg = "Low"
    factors.append({"name": "Urgency", "rating": urg})

    # ---- Signals analyzed (labeled rows for the "Why this recommendation?" screen) ----
    # available=True → we actually have the signal (green check); False → not connected yet.
    signals: list[dict] = []
    if scheduled_at_label:
        cal = f"This is on your calendar for {scheduled_at_label}."
    elif off_hours:
        cal = "You're outside your working hours right now."
    elif next_event:
        cal = f"You have a {free_minutes}-minute free block before {next_event}."
    else:
        cal = f"You have {free_minutes} minutes free before your workday ends."
    signals.append({"name": "Calendar", "detail": cal, "available": True})
    signals.append({"name": "Time of day", "detail": f"This is {tod_note} based on your routine.", "available": True})
    if place is not None and place.place_name:
        signals.append({"name": "Location", "detail": f"You're currently at {place.place_name}.", "available": True})
    elif place is not None:
        signals.append({"name": "Location", "detail": "You're out and about right now — a good time for errands.", "available": True})
    else:
        signals.append({"name": "Location", "detail": "No location signal connected yet.", "available": False})
    signals.append({"name": "Priority", "detail": f"This task is marked {_priority_label(best.priority).lower()} priority.", "available": True})
    if health:
        detail = f"{health['energy'].capitalize()} energy. {health['reason']}"
        signals.append({"name": "Energy", "detail": detail, "available": True})
    else:
        signals.append({"name": "Energy", "detail": "No sleep or activity signal connected yet.", "available": False})

    # ---- Confidence: reflects the pick's real engine score (shared source with /now + recommendation) ----
    confidence = score_to_confidence(score)

    # ---- Alternatives considered ----
    # `best` isn't always the top-ranked task — when the user opens the Why sheet for an alternative,
    # the real top pick shows up here. Comparing purely against `best` then mislabelled that stronger,
    # higher-scored task as "a slightly weaker fit" (TIME-247). So when we know an alternative outscored
    # the explained task, say so instead of calling it weaker.
    alts = []
    scores = alt_scores or {}
    for a in alternatives:
        a_score = scores.get(str(a.id))
        if a_score is not None and a_score > score:
            reason = "Ranked higher overall — the stronger pick right now."
        elif a.priority > best.priority:
            reason = "Lower priority than this task."
        elif a.estimated_minutes and est and a.estimated_minutes < est:
            reason = "Fits a shorter block you can do later."
        elif a.due_at is None and best.due_at is not None:
            reason = "No deadline pressure, so it can wait."
        else:
            reason = "A solid option, but a slightly weaker fit for right now."
        alts.append({"task_id": str(a.id), "title": a.title, "reason_not_selected": reason})

    # ---- Summary (LLM, deterministic fallback) ----
    summary = await _summarise(best, context_used, gateway)

    return {
        "recommended_action": {
            "task_id": str(best.id),
            "title": best.title,
            "recommended_duration_minutes": best.estimated_minutes,
        },
        "confidence": confidence,
        "context_used": context_used,
        "decision_factors": factors,
        "signals": signals,
        "alternatives_considered": alts,
        "summary": summary,
    }


async def _summarise(best, context_used: list[str], gateway) -> str:
    fallback = (
        f"TimeSense picked this because it's the best fit for your current time, schedule, and task "
        f"priorities."
    )
    try:
        prompt = "Chosen task: '" + best.title + "'\nContext:\n" + "\n".join(f"- {c}" for c in context_used)
        text = await gateway.complete_simple(prompt, system=_SUMMARY_SYSTEM, max_tokens=110)
        return text.strip() or fallback
    except Exception:
        return fallback
