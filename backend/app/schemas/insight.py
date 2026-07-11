from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class WeeklyInsightResponse(BaseModel):
    week_start: date
    week_end: date
    tasks_completed: int
    tasks_total: int
    completion_rate: float | None
    most_skipped_meal: str | None
    late_wake_count: int
    commute_confirmed_count: int
    feedback_done_count: int
    feedback_not_now_count: int
    recommendations_shown: int
    recommendations_accepted: int
    recommendation_acceptance_rate: float | None
    mean_confidence: float | None
    summary_text: str

    model_config = {"from_attributes": True}
