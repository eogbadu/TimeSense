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
from typing import Sequence
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commute import CommuteEvent
from app.models.sleep_wake import SleepWakeEvent
from app.services.usable_time_service import UsableTimeService

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
    """Latest sleep/wake for today → (wake_time_local_str, sleep_hours, energy_estimate) or None."""
    today = _local(now, tz_name).date()
    rows = (await db.execute(
        select(SleepWakeEvent)
        .where(SleepWakeEvent.user_id == user_id)
        .order_by(SleepWakeEvent.wake_time.desc())
        .limit(1)
    )).scalars().all()
    if not rows:
        return None
    ev = rows[0]
    wake_local = _local(_utc(ev.wake_time), tz_name)
    if wake_local.date() != today:
        return None
    sleep_hours = None
    if ev.sleep_start is not None:
        sleep_hours = round((_utc(ev.wake_time) - _utc(ev.sleep_start)).total_seconds() / 3600, 1)
    if sleep_hours is None:
        energy = "moderate"
    elif sleep_hours >= 7.5:
        energy = "high"
    elif sleep_hours >= 6:
        energy = "moderate"
    else:
        energy = "low"
    return wake_local.strftime("%-I:%M %p"), sleep_hours, energy


async def _location(db: AsyncSession, user_id, now: datetime):
    """Recent commute → 'commuting' if a window is active near now, 'settled' if one earlier today,
    else None (we have no reliable place signal)."""
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


def _next_event(today_tasks: Sequence, now: datetime, tz_name: str):
    upcoming = [
        t for t in today_tasks
        if t.scheduled_start is not None and _utc(t.scheduled_start) > now and t.status != "done"
    ]
    if not upcoming:
        return None
    nxt = min(upcoming, key=lambda t: _utc(t.scheduled_start))
    return f"{nxt.title} at {_local(_utc(nxt.scheduled_start), tz_name).strftime('%-I:%M %p')}"


async def build_explanation(
    db: AsyncSession,
    user,
    best,
    alternatives: Sequence,
    today_tasks: Sequence,
    now: datetime,
    tz_name: str,
    gateway,
) -> dict:
    free_minutes = UsableTimeService().calculate(list(today_tasks), anchor=now, user_timezone=tz_name)
    local_now = _local(now, tz_name)
    tod_label, tod_note = _time_of_day(local_now)
    next_event = _next_event(today_tasks, now, tz_name)
    health = await _health(db, user.id, now, tz_name)
    location = await _location(db, user.id, now)

    est = best.estimated_minutes or 0
    fits = est <= free_minutes if est else True

    # ---- Context used (human bullets, only what we actually know) ----
    context_used: list[str] = []
    if next_event:
        context_used.append(f"Calendar: {free_minutes} minutes free before {next_event}.")
    else:
        context_used.append(f"Calendar: {free_minutes} minutes free before the end of your day.")
    context_used.append(f"Time of day: it's {tod_label} — {tod_note}.")
    if location == "commuting":
        context_used.append("Location: you appear to be commuting right now.")
    elif location == "settled":
        context_used.append("Location: you're settled (no active commute).")
    if health:
        wake_str, sleep_hours, energy = health
        slp = f" on {sleep_hours}h of sleep" if sleep_hours else ""
        context_used.append(f"Energy: estimated {energy} (woke at {wake_str}{slp}).")
    if est:
        context_used.append(
            f"Task: {_priority_label(best.priority).lower()} priority, ~{est} min — "
            + ("fits the time you have." if fits else "longer than the time you have right now.")
        )

    # ---- Decision factors (deterministic ratings) ----
    factors = [{"name": "Priority", "rating": _priority_label(best.priority)}]
    if est:
        factors.append({"name": "Time fit", "rating": "Strong" if fits else ("Partial" if est <= free_minutes * 1.5 else "Tight")})
    if health:
        energy = health[2]
        factors.append({"name": "Energy match", "rating": "Good" if energy in ("high", "moderate") else "Low"})
    if location is not None:
        factors.append({"name": "Location fit", "rating": "Good" if location == "settled" else "Limited"})
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

    # ---- Confidence (heuristic, explainable) ----
    conf = 0.70
    if est and fits:
        conf += 0.10
    if best.priority <= 2:
        conf += 0.06
    if urg in ("High", "Medium"):
        conf += 0.05
    if est and not fits:
        conf -= 0.15
    if len(alternatives) == 0:
        conf += 0.05
    confidence = round(max(0.5, min(0.95, conf)), 2)

    # ---- Alternatives considered ----
    alts = []
    for a in alternatives:
        if a.priority > best.priority:
            reason = "Lower priority than the top pick."
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
