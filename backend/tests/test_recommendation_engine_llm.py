"""TIME-117 — LLM explanation layer. The LLM only writes text; it never changes the decision, and
any failure falls back to deterministic text."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.recommendation.engine import run_engine
from app.services.recommendation.llm.fallback_recommendation_text import fallback_text
from app.services.recommendation.llm.generate_recommendation_text import (
    generate_recommendation_text,
)
from app.services.recommendation.normalize_context import RawContextInputs, normalize_context
from app.services.recommendation.time_service import get_time_snapshot
from app.services.recommendation.types import TaskItem, UserPreferences

pytestmark = pytest.mark.anyio

NOW = datetime(2026, 7, 6, 14, 0, tzinfo=timezone.utc)


class _Gateway:
    """Stub LLM gateway. `reply` is returned verbatim, or `raises` to simulate an outage."""

    def __init__(self, reply: str = "", raises: bool = False):
        self.reply, self.raises, self.calls = reply, raises, 0

    async def complete_simple(self, prompt, system="", max_tokens=1024):
        self.calls += 1
        if self.raises:
            raise RuntimeError("llm down")
        return self.reply


def _ctx(tasks):
    raw = RawContextInputs(now=NOW, timezone="UTC", time_snapshot=get_time_snapshot("UTC", now=NOW),
                           preferences=UserPreferences(preferred_tone="calm"), tasks=tasks)
    return normalize_context(raw)


def _task():
    return TaskItem(id="t1", title="Finish the report", source="manual", priority="high",
                    status="not_started", estimated_minutes=40,
                    due_date=(NOW + timedelta(hours=2)).isoformat())


async def _rec():
    return await run_engine(_ctx([_task()]), now=NOW)


async def test_fallback_text_uses_recommendation_fields():
    rec = await _rec()
    text = fallback_text(rec)
    assert text.notification_title == rec.title
    assert text.notification_body and text.explanation


async def test_llm_parses_valid_json():
    rec = await _rec()
    gw = _Gateway(reply='{"notification_title": "Focus now", "notification_body": "Give the report '
                        '40 minutes.", "explanation": "It is high priority and due soon."}')
    text = await generate_recommendation_text(rec, _ctx([_task()]), gw)
    assert text.notification_title == "Focus now"
    assert "40 minutes" in text.notification_body
    assert gw.calls == 1


async def test_llm_handles_json_wrapped_in_markdown():
    rec = await _rec()
    gw = _Gateway(reply='```json\n{"notification_title":"A","notification_body":"B","explanation":"C"}\n```')
    text = await generate_recommendation_text(rec, _ctx([_task()]), gw)
    assert (text.notification_title, text.notification_body, text.explanation) == ("A", "B", "C")


async def test_llm_failure_falls_back():
    rec = await _rec()
    gw = _Gateway(raises=True)
    text = await generate_recommendation_text(rec, _ctx([_task()]), gw)
    assert text.notification_title == rec.title  # deterministic fallback


async def test_llm_garbage_falls_back():
    rec = await _rec()
    gw = _Gateway(reply="not json at all")
    text = await generate_recommendation_text(rec, _ctx([_task()]), gw)
    assert text.explanation == (rec.explanation or rec.message)


async def test_run_engine_with_gateway_sets_text_but_not_action():
    ctx = _ctx([_task()])
    deterministic = await run_engine(ctx, now=NOW)
    gw = _Gateway(reply='{"notification_title":"Do X instead","notification_body":"body",'
                        '"explanation":"why"}')
    with_llm = await run_engine(ctx, now=NOW, gateway=gw)
    # LLM rewrote the text …
    assert with_llm.explanation == "why" and with_llm.message == "body"
    # … but the ENGINE's decision is unchanged (LLM can't pick a different action).
    assert with_llm.action_type == deterministic.action_type
    assert with_llm.domain == deterministic.domain


async def test_run_engine_without_gateway_is_deterministic():
    rec = await run_engine(_ctx([_task()]), now=NOW)
    assert rec.explanation and rec.reason_codes  # deterministic text, no LLM call
