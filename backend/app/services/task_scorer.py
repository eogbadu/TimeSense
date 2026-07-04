from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence

from app.models.task import Task


class TaskScorer:
    """
    Scores pending task candidates. Lower score = higher priority.

    Factors (all additive):
      priority_score   — maps priority 1→0.0 … 5→1.0  (weight 0.5)
      deadline_score   — overdue→0.0, due today→0.2, within 3 days→0.4, future→0.8  (weight 0.35)
      duration_score   — fits in usable window→0.0, no estimate→0.1, exceeds window→0.3  (weight 0.15)
    """

    def score(self, task: Task, usable_minutes: int, now: datetime | None = None) -> float:
        now = now or datetime.now(timezone.utc)

        # Priority (1=best → 0.0, 5=worst → 1.0)
        priority_score = (task.priority - 1) / 4.0

        # Deadline urgency
        deadline_score = self._deadline_score(task, now)

        # Duration fit
        duration_score = self._duration_score(task, usable_minutes)

        return 0.5 * priority_score + 0.35 * deadline_score + 0.15 * duration_score

    def rank(
        self,
        tasks: Sequence[Task],
        usable_minutes: int,
        now: datetime | None = None,
    ) -> list[Task]:
        now = now or datetime.now(timezone.utc)
        return sorted(tasks, key=lambda t: self.score(t, usable_minutes, now))

    def _deadline_score(self, task: Task, now: datetime) -> float:
        if task.due_at is None:
            return 0.6  # no deadline — medium urgency

        due = task.due_at
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)

        delta = due - now
        if delta.total_seconds() <= 0:
            return 0.0  # overdue
        if delta < timedelta(hours=24):
            return 0.2  # due today
        if delta < timedelta(days=3):
            return 0.4  # due soon
        return 0.8  # future

    def _duration_score(self, task: Task, usable_minutes: int) -> float:
        if task.estimated_minutes is None:
            return 0.1  # slight penalty for unknown duration
        if task.estimated_minutes <= usable_minutes:
            return 0.0  # fits perfectly
        return 0.3  # too long for the current window
