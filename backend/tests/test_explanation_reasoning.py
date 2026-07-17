"""TIME-243 — a task scheduled for a future time is explained by its own time, not a generic
'free before your next meeting' line (which read nonsensically for e.g. a 4pm appointment)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.llm.gateway import get_llm_gateway
from app.models.task import Task
from app.services.recommendation_explainer import build_explanation
from app.services.user_service import UserService


@pytest.mark.anyio
async def test_scheduled_task_uses_its_own_time_not_free_before_next(db_session):
    user, _ = await UserService(db_session).get_or_create_user("uid-expl-1", "expl1@example.com")
    now = datetime(2026, 7, 20, 9, 0, tzinfo=UTC)          # 9:00 AM
    appt = Task(user_id=user.id, title="Dentist appointment", status="pending", priority=3,
                scheduled_start=now + timedelta(hours=7),  # 4:00 PM
                scheduled_end=now + timedelta(hours=8))
    db_session.add(appt)
    await db_session.flush()

    exp = await build_explanation(
        db_session, user, appt, alternatives=[], today_tasks=[appt],
        now=now, tz_name="UTC", gateway=get_llm_gateway(),
    )
    cal_signal = next(s for s in exp["signals"] if s["name"] == "Calendar")["detail"]
    cal_context = next(c for c in exp["context_used"] if c.startswith("Calendar"))

    assert "4:00 PM" in cal_signal and "free block before" not in cal_signal
    assert "scheduled for 4:00 PM" in cal_context and "free before" not in cal_context


@pytest.mark.anyio
async def test_unscheduled_task_keeps_free_time_framing(db_session):
    user, _ = await UserService(db_session).get_or_create_user("uid-expl-2", "expl2@example.com")
    now = datetime(2026, 7, 20, 9, 0, tzinfo=UTC)
    task = Task(user_id=user.id, title="Write the report", status="pending", priority=2,
                estimated_minutes=30)
    db_session.add(task)
    await db_session.flush()

    exp = await build_explanation(
        db_session, user, task, alternatives=[], today_tasks=[task],
        now=now, tz_name="UTC", gateway=get_llm_gateway(),
    )
    cal_context = next(c for c in exp["context_used"] if c.startswith("Calendar"))
    assert "free before" in cal_context and "scheduled for" not in cal_context
