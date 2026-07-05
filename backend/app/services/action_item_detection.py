"""
Source-neutral action-item detection.

Shared by every message-source integration (Slack, Teams, …): given one chat message's text,
ask the LLM whether it's a genuine action item the reader must personally do, and if so extract a
task title/priority/estimate. Degrades to "not an action item" on any LLM failure — same graceful
fallback discipline as CaptureService.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.llm.gateway import LLMGateway

logger = logging.getLogger(__name__)

_DETECT_SYSTEM = """\
You decide whether a single chat message is an action item the reader needs to personally do.
Respond ONLY with a single valid JSON object — no markdown, no extra text.

JSON schema:
{
  "is_action_item": <true|false>,
  "title": "<concise action title, max 120 chars, empty string if not an action item>",
  "estimated_minutes": <integer or null>,
  "priority": <1 to 5 integer, 3 if unclear>
}

Rules:
- is_action_item is true ONLY for a concrete task the reader must do (e.g. "can you send the
  report by Friday?"). Casual chat, FYIs, and questions already answered are NOT action items.
- title: a short actionable phrase, not the raw message. Empty string when is_action_item is false.
- priority: 1=critical, 2=high, 3=normal, 4=low, 5=someday
- Respond with raw JSON only — no code fences, no explanation.
"""


@dataclass
class Detection:
    is_action_item: bool
    title: str = ""
    estimated_minutes: int | None = None
    priority: int = 3


class ActionItemDetectionService:
    """Isolated so the LLM detection logic is unit-testable without the DB/service layer."""

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway

    async def detect(self, message_text: str) -> Detection:
        try:
            raw = await self._gateway.complete_simple(
                prompt=f"Message:\n{message_text}",
                system=_DETECT_SYSTEM,
                max_tokens=128,
            )
            parsed = json.loads(raw.strip())
            if not parsed.get("is_action_item"):
                return Detection(is_action_item=False)
            title = str(parsed.get("title") or "").strip()
            if not title:
                return Detection(is_action_item=False)
            return Detection(
                is_action_item=True,
                title=title[:500],
                estimated_minutes=_safe_int(parsed.get("estimated_minutes")),
                priority=_clamp(int(parsed.get("priority", 3)), 1, 5),
            )
        except Exception as exc:  # noqa: BLE001 — graceful degradation, same as CaptureService
            logger.warning("Action-item detection failed, treating as non-action: %s", exc)
            return Detection(is_action_item=False)


def _safe_int(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))
