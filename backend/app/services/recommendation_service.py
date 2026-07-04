from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from app.llm.gateway import LLMGateway
from app.models.task import Task
from app.services.task_scorer import TaskScorer
from app.services.usable_time_service import UsableTimeService

_EXPLAIN_SYSTEM = (
    "You are a concise personal time assistant. "
    "Reply with exactly one sentence (≤ 20 words) explaining why this task is the best choice right now. "
    "No preamble, no bullet points — just the sentence."
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
    ) -> tuple[Task | None, list[Task], int, str | None]:
        """
        Returns (best_task, alternatives, usable_minutes, why).
        alternatives: up to 2 runner-up tasks.
        why: one-sentence LLM explanation, or a fallback string.
        """
        now = now or datetime.now(timezone.utc)
        usable = _usable_svc.calculate(list(scheduled_tasks), anchor=now)

        candidates = [t for t in tasks if t.status in ("pending", "in_progress")]
        if not candidates:
            return None, [], usable, None

        ranked = _scorer.rank(candidates, usable, now)
        best = ranked[0]
        alternatives = ranked[1:3]

        why = await self._explain(best, usable, now)
        return best, alternatives, usable, why

    async def _explain(self, task: Task, usable_minutes: int, now: datetime) -> str:
        try:
            prompt = (
                f"Task: '{task.title}'\n"
                f"Priority: {task.priority}/5\n"
                f"Due: {task.due_at.isoformat() if task.due_at else 'no deadline'}\n"
                f"Estimated: {task.estimated_minutes or 'unknown'} min\n"
                f"Usable time available: {usable_minutes} min\n"
                f"Current time UTC: {now.isoformat()}"
            )
            text = await self._gateway.complete_simple(prompt, system=_EXPLAIN_SYSTEM, max_tokens=60)
            return text.strip()
        except Exception:
            return _fallback_why(task, now)


def _fallback_why(task: Task, now: datetime) -> str:
    if task.due_at:
        due = task.due_at
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if due < now:
            return "This task is overdue and needs your attention."
        delta_h = (due - now).total_seconds() / 3600
        if delta_h < 24:
            return "This task is due today."
    if task.priority == 1:
        return "This is your highest-priority task."
    return "This task is the best fit for your available time."
