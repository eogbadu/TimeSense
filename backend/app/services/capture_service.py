"""
Capture service — converts raw user text into a structured TaskCreate.
Uses the LLM Gateway for parsing; falls back gracefully if unavailable.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.llm.base import LLMRequest
from app.llm.gateway import LLMGateway
from app.schemas.task import TaskCreate

logger = logging.getLogger(__name__)

_PARSE_SYSTEM = """\
You are a task extraction assistant. The user gives you a raw piece of text describing
something they need to do. Extract structured task information and respond ONLY with
a single valid JSON object — no markdown, no extra text.

JSON schema:
{
  "title": "<concise action title, max 120 chars>",
  "estimated_minutes": <integer or null>,
  "due_at": "<ISO 8601 UTC datetime string or null>",
  "priority": <1 to 5 integer, 3 if unclear>
}

Rules:
- title must be a short, actionable phrase (not the full raw text)
- estimated_minutes: derive from hints like "30 min", "an hour", "quick"; null if not mentioned
- due_at: convert relative dates like "tomorrow 2pm" to absolute UTC; null if not mentioned
- priority: 1=critical, 2=high, 3=normal, 4=low, 5=someday
- Respond with raw JSON only — no code fences, no explanation
"""


class CaptureService:
    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway

    async def parse(self, raw_input: str, user_timezone: str = "UTC") -> TaskCreate:
        prompt = (
            f"Today's UTC date and time: {datetime.now(timezone.utc).isoformat()}\n"
            f"User timezone: {user_timezone}\n\n"
            f"Raw input: {raw_input}"
        )
        try:
            raw_json = await self._gateway.complete_simple(
                prompt=prompt,
                system=_PARSE_SYSTEM,
                max_tokens=256,
            )
            parsed = json.loads(raw_json.strip())
            due_at: datetime | None = None
            if parsed.get("due_at"):
                try:
                    due_at = datetime.fromisoformat(parsed["due_at"].replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    due_at = None
            return TaskCreate(
                title=str(parsed.get("title") or raw_input)[:500],
                estimated_minutes=_safe_int(parsed.get("estimated_minutes")),
                due_at=due_at,
                priority=_clamp(int(parsed.get("priority", 3)), 1, 5),
                source="capture",
                raw_input=raw_input,
            )
        except Exception as exc:
            logger.warning("Capture parse failed, falling back to raw title: %s", exc)
            return TaskCreate(
                title=raw_input[:500],
                source="capture",
                raw_input=raw_input,
            )


def _safe_int(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))
