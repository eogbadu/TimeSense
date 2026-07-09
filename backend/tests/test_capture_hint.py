"""TIME-163 — capture type_hint biases the parse (Idea -> low priority)."""
import pytest
from app.services.capture_service import CaptureService
from app.llm.gateway import get_llm_gateway


@pytest.mark.anyio
async def test_idea_hint_forces_low_priority_and_no_schedule():
    svc = CaptureService(get_llm_gateway())
    tc = await svc.parse("build a personal website someday", user_timezone="UTC", type_hint="Idea")
    assert tc.priority == 5
    assert tc.scheduled_start is None


@pytest.mark.anyio
async def test_no_hint_is_unchanged():
    svc = CaptureService(get_llm_gateway())
    tc = await svc.parse("buy milk", user_timezone="UTC", type_hint=None)
    assert tc.title  # still parses
