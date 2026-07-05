from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.gateway import LLMGateway
from app.models.insight import WeeklyInsight
from app.repositories.commute_repository import CommuteRepository
from app.repositories.insight_repository import InsightRepository
from app.repositories.meal_repository import MealRepository
from app.repositories.recommendation_feedback_repository import RecommendationFeedbackRepository
from app.repositories.sleep_wake_repository import SleepWakeRepository
from app.repositories.task_repository import TaskRepository

_SUMMARY_SYSTEM = (
    "You are a calm, encouraging personal time assistant summarizing a user's past week. "
    "Write 2-3 sentences, no bullet points, no guilt-inducing language. Focus on patterns "
    "and gentle encouragement, not judgment."
)


def most_recently_completed_week(today: date) -> tuple[date, date]:
    """The most recently fully-elapsed Monday-Sunday week, strictly before the week
    containing `today`."""
    this_week_monday = today - timedelta(days=today.weekday())
    week_start = this_week_monday - timedelta(days=7)
    week_end = this_week_monday - timedelta(days=1)
    return week_start, week_end


class InsightsService:
    def __init__(self, db: AsyncSession, gateway: LLMGateway) -> None:
        self.db = db
        self._gateway = gateway
        self.insight_repo = InsightRepository(db)
        self.task_repo = TaskRepository(db)
        self.feedback_repo = RecommendationFeedbackRepository(db)
        self.meal_repo = MealRepository(db)
        self.sleep_repo = SleepWakeRepository(db)
        self.commute_repo = CommuteRepository(db)

    async def get_or_generate_latest(self, user_id: uuid.UUID) -> WeeklyInsight:
        week_start, week_end = most_recently_completed_week(datetime.now(timezone.utc).date())
        return await self.get_or_generate_for_week(user_id, week_start, week_end)

    async def get_or_generate_for_week(
        self, user_id: uuid.UUID, week_start: date, week_end: date
    ) -> WeeklyInsight:
        """Idempotent: a week that's already been generated is returned as-is, never
        silently recomputed (past weeks don't change)."""
        existing = await self.insight_repo.get_by_week(user_id, week_start)
        if existing is not None:
            return existing
        return await self._generate(user_id, week_start, week_end)

    async def _generate(
        self, user_id: uuid.UUID, week_start: date, week_end: date
    ) -> WeeklyInsight:
        start_dt = datetime(week_start.year, week_start.month, week_start.day, tzinfo=timezone.utc)
        end_dt = start_dt + timedelta(days=7)

        tasks_total = await self.task_repo.count_created_in_range(user_id, start_dt, end_dt)
        tasks_completed = await self.task_repo.count_completed_in_range(user_id, start_dt, end_dt)
        completion_rate = tasks_completed / tasks_total if tasks_total > 0 else None

        skipped_by_meal = await self.meal_repo.count_skipped_by_type_in_range(
            user_id, start_dt, end_dt
        )
        most_skipped_meal = (
            min(skipped_by_meal.items(), key=lambda kv: (-kv[1], kv[0]))[0]
            if skipped_by_meal
            else None
        )

        late_wake_count = await self.sleep_repo.count_late_wakes_in_range(user_id, start_dt, end_dt)
        commute_confirmed_count = await self.commute_repo.count_confirmed_in_range(
            user_id, start_dt, end_dt
        )

        signal_counts = await self.feedback_repo.count_signals_in_range(user_id, start_dt, end_dt)

        stats = {
            "week_start": week_start,
            "week_end": week_end,
            "tasks_completed": tasks_completed,
            "tasks_total": tasks_total,
            "completion_rate": completion_rate,
            "most_skipped_meal": most_skipped_meal,
            "late_wake_count": late_wake_count,
            "commute_confirmed_count": commute_confirmed_count,
            "feedback_done_count": signal_counts.get("done", 0),
            "feedback_not_now_count": signal_counts.get("not_now", 0),
        }
        summary_text = await self._summarize(stats)

        return await self.insight_repo.create(user_id=user_id, summary_text=summary_text, **stats)

    async def _summarize(self, stats: dict) -> str:
        try:
            prompt = (
                f"Week: {stats['week_start'].isoformat()} to {stats['week_end'].isoformat()}\n"
                f"Tasks completed: {stats['tasks_completed']} of {stats['tasks_total']} created\n"
                f"Most skipped meal: {stats['most_skipped_meal'] or 'none logged'}\n"
                f"Late wake-ups: {stats['late_wake_count']}\n"
                f"Confirmed commutes: {stats['commute_confirmed_count']}\n"
                f"Recommendations marked done: {stats['feedback_done_count']}, "
                f"dismissed with not now: {stats['feedback_not_now_count']}"
            )
            text = await self._gateway.complete_simple(
                prompt, system=_SUMMARY_SYSTEM, max_tokens=120
            )
            return text.strip()
        except Exception:
            return _fallback_summary(stats)


def _fallback_summary(stats: dict) -> str:
    parts: list[str] = []
    if stats["tasks_total"] > 0:
        parts.append(
            f"You completed {stats['tasks_completed']} of {stats['tasks_total']} "
            "tasks this week."
        )
    else:
        parts.append("No new tasks were captured this week.")
    if stats["most_skipped_meal"]:
        parts.append(
            f"{stats['most_skipped_meal'].capitalize()} was the meal you skipped most often."
        )
    if stats["late_wake_count"] > 0:
        parts.append(f"You woke up later than usual {stats['late_wake_count']} time(s).")
    return " ".join(parts)
