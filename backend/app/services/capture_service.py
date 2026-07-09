"""
Capture service — converts raw user text into a structured TaskCreate.
Uses the LLM Gateway for parsing; falls back gracefully if unavailable.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from app.llm.base import LLMRequest
from app.llm.gateway import LLMGateway
from app.schemas.task import TaskCreate
from app.services.capture_date_parser import parse_datetime

logger = logging.getLogger(__name__)

_PARSE_SYSTEM = """\
You are a task extraction assistant. The user gives you a raw piece of text describing
something they need to do. Extract structured task information and respond ONLY with
a single valid JSON object — no markdown, no extra text.

JSON schema:
{
  "title": "<concise action title, max 120 chars>",
  "estimated_minutes": <integer or null>,
  "scheduled_start": "<ISO 8601 UTC datetime or null>",
  "due_at": "<ISO 8601 UTC datetime or null>",
  "priority": <1 to 5 integer, 3 if unclear>
}

Rules:
- title must be a short, actionable phrase (not the full raw text)
- estimated_minutes: derive from hints like "30 min", "an hour", "quick"; null if not mentioned
- scheduled_start: set ONLY when the user gives a SPECIFIC clock time to do it
  (e.g. "today at 5pm", "tomorrow 2pm", "9:30am Monday"). Convert to absolute UTC.
- due_at: a deadline/date WITHOUT a specific do-time (e.g. "by Friday", "July 5th", "due tomorrow").
  Convert to absolute UTC. If a specific time is given, prefer scheduled_start and leave due_at null.
- priority: 1=critical, 2=high, 3=normal, 4=low, 5=someday
- Respond with raw JSON only — no code fences, no explanation
"""


# Optional per-capture type hints from the Capture chips — bias the parse toward the user's intent.
_HINT_GUIDANCE = {
    "task": "Treat it as a concrete to-do.",
    "reminder": "Treat it as a time-sensitive reminder; capture any time as scheduled_start.",
    "schedule": "Treat it as a calendar event; set scheduled_start when a time is given.",
    "errand": "Treat it as a location-based errand (something done at a place).",
    "idea": "Treat it as a low-priority someday idea — no deadline or scheduled time.",
}


class CaptureService:
    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway

    async def parse(
        self, raw_input: str, user_timezone: str = "UTC", type_hint: str | None = None
    ) -> TaskCreate:
        # Deterministic extraction runs regardless — it reliably handles the common phrasings
        # ("today at 5pm", "July 5th") that the LLM sometimes drops, and fills any gaps below.
        rb_start, rb_due, rb_title = parse_datetime(raw_input, user_timezone=user_timezone)

        hint = _HINT_GUIDANCE.get((type_hint or "").lower())
        hint_line = f"\nThe user tagged this as a {type_hint}. {hint}\n" if hint else ""
        prompt = (
            f"Today's UTC date and time: {datetime.now(timezone.utc).isoformat()}\n"
            f"User timezone: {user_timezone}\n"
            f"{hint_line}\n"
            f"Raw input: {raw_input}"
        )
        try:
            raw_json = await self._gateway.complete_simple(
                prompt=prompt, system=_PARSE_SYSTEM, max_tokens=256,
            )
            parsed = json.loads(raw_json.strip())
            # LLM values win when present; the deterministic parser fills the gaps.
            scheduled_start = _parse_iso(parsed.get("scheduled_start")) or rb_start
            due_at = _parse_iso(parsed.get("due_at")) or rb_due
            estimated = _safe_int(parsed.get("estimated_minutes"))
            title = str(parsed.get("title") or rb_title)[:500]
            priority = _clamp(int(parsed.get("priority", 3)), 1, 5)
        except Exception as exc:
            logger.warning("Capture parse failed, using rule-based fallback: %s", exc)
            scheduled_start, due_at, estimated, title, priority = (
                rb_start, rb_due, None, rb_title[:500], 3
            )

        # An "Idea" is a someday capture — never urgent, never auto-scheduled.
        if (type_hint or "").lower() == "idea":
            priority = 5
            scheduled_start = None

        # A "do it at 5pm" gets a concrete block; give it a length so it lands on the timeline.
        scheduled_end = (
            scheduled_start + timedelta(minutes=estimated or 30)
            if scheduled_start is not None else None
        )
        return TaskCreate(
            title=title, estimated_minutes=estimated,
            scheduled_start=scheduled_start, scheduled_end=scheduled_end,
            due_at=due_at, priority=priority, source="capture", raw_input=raw_input,
        )


def _parse_iso(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None


def _safe_int(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))
