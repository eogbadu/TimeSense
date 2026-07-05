from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
from zoneinfo import ZoneInfo

from app.llm.gateway import LLMGateway
from app.models.task import Task
from app.services.task_scorer import TaskScorer
from app.services.usable_time_service import UsableTimeService

_EXPLAIN_SYSTEM = (
    "You are a calm, concise personal time assistant. In one or two short sentences "
    "(≤ 35 words total), explain why the chosen task is the best thing to do RIGHT NOW compared "
    "with the other options — weighing the time of day and the user's likely energy, the free time "
    "available before their next commitment, and any deadlines. Speak directly to the user ('you'). "
    "No preamble, no lists, no restating the task title verbatim."
)

_scorer = TaskScorer()
_usable_svc = UsableTimeService()


class RecommendationService:
    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway

    async def recommend(
        self,
        tasks: Sequence[Task],
        scheduled_tasks: Sequence[Task],
        now: datetime | None = None,
        user_timezone: str = "UTC",
    ) -> tuple[Task | None, list[Task], int, str | None]:
        """
        Returns (best_task, alternatives, usable_minutes, why).
        alternatives: up to 2 runner-up tasks.
        why: one/two-sentence LLM explanation that weighs the alternatives, time of day, likely
        energy, free time, and deadlines — or a deterministic fallback when the LLM is unavailable.
        """
        now = now or datetime.now(timezone.utc)
        usable = _usable_svc.calculate(list(scheduled_tasks), anchor=now)

        candidates = [t for t in tasks if t.status in ("pending", "in_progress")]
        if not candidates:
            return None, [], usable, None

        ranked = _scorer.rank(candidates, usable, now)
        best = ranked[0]
        alternatives = ranked[1:3]

        why = await self.explain_choice(best, alternatives, usable, now, user_timezone)
        return best, alternatives, usable, why

    async def explain_choice(
        self,
        task: Task,
        alternatives: Sequence[Task],
        usable_minutes: int,
        now: datetime,
        user_timezone: str = "UTC",
    ) -> str:
        part, energy = _part_of_day(now, user_timezone)
        try:
            alt_lines = "\n".join(f"  - {_task_line(a)}" for a in alternatives) or "  (none)"
            prompt = (
                f"Time of day: {part} — {energy}.\n"
                f"Free time before the next commitment: {usable_minutes} min.\n"
                f"Chosen task: {_task_line(task)}\n"
                f"Other options not chosen:\n{alt_lines}\n\n"
                "Explain why the chosen task is the best move right now versus the other options."
            )
            text = await self._gateway.complete_simple(prompt, system=_EXPLAIN_SYSTEM, max_tokens=80)
            cleaned = text.strip()
            return cleaned or _fallback_why(task, alternatives, usable_minutes, now, user_timezone)
        except Exception:
            return _fallback_why(task, alternatives, usable_minutes, now, user_timezone)


def _task_line(task: Task) -> str:
    due = "no deadline"
    if task.due_at:
        due_dt = task.due_at if task.due_at.tzinfo else task.due_at.replace(tzinfo=timezone.utc)
        due = due_dt.date().isoformat()
    est = f"{task.estimated_minutes} min" if task.estimated_minutes else "unknown length"
    return f"'{task.title}' (priority {task.priority}/5, due {due}, {est})"


def _part_of_day(now: datetime, user_timezone: str) -> tuple[str, str]:
    try:
        local = now.astimezone(ZoneInfo(user_timezone))
    except Exception:
        local = now
    h = local.hour
    if 5 <= h < 11:
        return "morning", "energy is usually fresh, good for focus or harder tasks"
    if 11 <= h < 14:
        return "midday", "a steady stretch before the afternoon"
    if 14 <= h < 17:
        return "afternoon", "energy can dip after lunch, so lighter tasks fit well"
    if 17 <= h < 21:
        return "evening", "winding down, better to wrap up than start heavy work"
    return "late", "low energy, keep it light or rest"


def _fallback_why(
    task: Task,
    alternatives: Sequence[Task],
    usable_minutes: int,
    now: datetime,
    user_timezone: str,
) -> str:
    """Deterministic explanation used when the LLM is unavailable (e.g. OpenAI quota)."""
    part, _ = _part_of_day(now, user_timezone)
    reasons: list[str] = []

    if task.due_at:
        due = task.due_at if task.due_at.tzinfo else task.due_at.replace(tzinfo=timezone.utc)
        if due < now:
            reasons.append("it's overdue")
        elif due.date() == now.date():
            reasons.append("it's due today")
    if task.priority and task.priority <= 2:
        reasons.append("it's your highest priority")
    if task.estimated_minutes and usable_minutes and task.estimated_minutes <= usable_minutes:
        reasons.append(f"it fits the {usable_minutes} minutes you have free")

    if reasons:
        if len(reasons) == 1:
            body = reasons[0]
        elif len(reasons) == 2:
            body = f"{reasons[0]} and {reasons[1]}"
        else:
            body = ", ".join(reasons[:-1]) + f", and {reasons[-1]}"
        lead = f"Best pick for the {part}: {body}"
    else:
        lead = f"A good fit for the {part} and your available time"

    if alternatives:
        return f"{lead} — ahead of {len(alternatives)} other option{'s' if len(alternatives) > 1 else ''} right now."
    return lead + "."
