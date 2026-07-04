from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.task_scorer import TaskScorer

ANCHOR = datetime(2026, 7, 4, 14, 0, 0, tzinfo=timezone.utc)


def _task(
    priority: int = 3,
    due_offset_hours: float | None = None,
    estimated_minutes: int | None = None,
    status: str = "pending",
) -> SimpleNamespace:
    due_at = None
    if due_offset_hours is not None:
        due_at = ANCHOR + timedelta(hours=due_offset_hours)
    return SimpleNamespace(
        priority=priority,
        due_at=due_at,
        estimated_minutes=estimated_minutes,
        status=status,
    )


class TestTaskScorer:
    svc = TaskScorer()

    def test_priority_1_scores_lower_than_priority_5(self) -> None:
        t1 = _task(priority=1)
        t5 = _task(priority=5)
        assert self.svc.score(t1, 60, ANCHOR) < self.svc.score(t5, 60, ANCHOR)

    def test_overdue_scores_lower_than_future_same_priority(self) -> None:
        overdue = _task(priority=3, due_offset_hours=-2)
        future = _task(priority=3, due_offset_hours=48)
        assert self.svc.score(overdue, 60, ANCHOR) < self.svc.score(future, 60, ANCHOR)

    def test_due_today_scores_lower_than_due_in_3_days(self) -> None:
        today = _task(priority=3, due_offset_hours=2)
        soon = _task(priority=3, due_offset_hours=60)
        assert self.svc.score(today, 60, ANCHOR) < self.svc.score(soon, 60, ANCHOR)

    def test_task_fits_window_scores_lower_than_task_exceeding(self) -> None:
        fits = _task(priority=3, estimated_minutes=30)
        exceeds = _task(priority=3, estimated_minutes=90)
        assert self.svc.score(fits, 60, ANCHOR) < self.svc.score(exceeds, 60, ANCHOR)

    def test_rank_returns_sorted_ascending(self) -> None:
        t_low = _task(priority=5, due_offset_hours=72)
        t_high = _task(priority=1, due_offset_hours=-1)
        t_mid = _task(priority=3, due_offset_hours=12)
        ranked = self.svc.rank([t_low, t_high, t_mid], 60, ANCHOR)
        scores = [self.svc.score(t, 60, ANCHOR) for t in ranked]
        assert scores == sorted(scores)

    def test_rank_first_is_best(self) -> None:
        t_urgent = _task(priority=1, due_offset_hours=1, estimated_minutes=30)
        t_lazy = _task(priority=5, due_offset_hours=100)
        ranked = self.svc.rank([t_lazy, t_urgent], 60, ANCHOR)
        assert ranked[0] is t_urgent

    def test_no_deadline_scores_mid_range(self) -> None:
        t_no_dl = _task(priority=3)
        score = self.svc.score(t_no_dl, 60, ANCHOR)
        assert 0.0 < score < 1.0

    def test_score_in_0_to_1_range(self) -> None:
        for p in range(1, 6):
            for hours in [-5, 0, 6, 48, 200]:
                t = _task(priority=p, due_offset_hours=hours, estimated_minutes=30)
                s = self.svc.score(t, 60, ANCHOR)
                assert 0.0 <= s <= 1.0, f"score={s} out of range for priority={p}, hours={hours}"
