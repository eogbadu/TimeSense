"""
Slack integration service.

RULE: Detected action items NEVER become Tasks automatically. scan_channel() only creates
      pending SlackActionItem rows; confirm() is the single approval-gated path that creates a
      Task — mirroring the calendar-write approval pattern (request → approve).
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.message_source_base import MessageSourceProvider
from app.integrations.slack_source import SlackMessageSource
from app.llm.gateway import LLMGateway
from app.models.slack import SlackActionItem, SlackIntegration
from app.repositories.slack_repository import (
    SlackActionItemRepository,
    SlackIntegrationRepository,
)
from app.repositories.task_repository import TaskRepository

logger = logging.getLogger(__name__)

_DETECT_SYSTEM = """\
You decide whether a single Slack message is an action item the reader needs to personally do.
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

_PROVIDERS: dict[str, MessageSourceProvider] = {
    "slack": SlackMessageSource(),
}


@dataclass
class Detection:
    is_action_item: bool
    title: str = ""
    estimated_minutes: int | None = None
    priority: int = 3


class SlackNotConnected(Exception):
    """Raised when scanning is attempted without an active Slack integration."""


class SlackDetectionService:
    """Isolated so the LLM detection logic is unit-testable without the DB/service layer."""

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway

    async def detect(self, message_text: str) -> Detection:
        try:
            raw = await self._gateway.complete_simple(
                prompt=f"Slack message:\n{message_text}",
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
            logger.warning("Slack action-item detection failed, treating as non-action: %s", exc)
            return Detection(is_action_item=False)


class SlackService:
    def __init__(self, db: AsyncSession, gateway: LLMGateway) -> None:
        self.db = db
        self.integration_repo = SlackIntegrationRepository(db)
        self.item_repo = SlackActionItemRepository(db)
        self.task_repo = TaskRepository(db)
        self.detector = SlackDetectionService(gateway)

    # ── Token management ──────────────────────────────────────────────────────

    async def connect(
        self, user_id: uuid.UUID, access_token: str, team_id: str | None = None
    ) -> SlackIntegration:
        return await self.integration_repo.upsert(user_id, access_token, team_id)

    async def disconnect(self, user_id: uuid.UUID) -> bool:
        return await self.integration_repo.deactivate(user_id)

    # ── Scan (detect only — never creates Tasks) ──────────────────────────────

    async def scan_channel(
        self, user_id: uuid.UUID, channel: str, limit: int = 50
    ) -> tuple[int, list[SlackActionItem]]:
        integration = await self.integration_repo.get_active(user_id)
        if integration is None:
            raise SlackNotConnected("Slack is not connected.")

        provider = _PROVIDERS["slack"]
        messages = await provider.list_recent_messages(
            access_token=integration.access_token, channel=channel, limit=limit
        )

        detected: list[SlackActionItem] = []
        for message in messages:
            if await self.item_repo.exists_for_message(user_id, message.message_id):
                continue
            result = await self.detector.detect(message.text)
            if not result.is_action_item:
                continue
            item = await self.item_repo.create(
                user_id=user_id,
                channel=message.channel,
                message_ts=message.message_id,
                source_text=message.text,
                detected_title=result.title,
                detected_priority=result.priority,
                detected_estimated_minutes=result.estimated_minutes,
            )
            detected.append(item)
        return len(messages), detected

    # ── Approval gate ─────────────────────────────────────────────────────────

    async def list_pending(self, user_id: uuid.UUID) -> list[SlackActionItem]:
        return await self.item_repo.list_pending(user_id)

    async def confirm(self, user_id: uuid.UUID, item_id: uuid.UUID) -> SlackActionItem:
        """Create a real Task from a pending item. The only path that turns Slack into a Task.
        Raises ValueError if not found or already handled."""
        item = await self.item_repo.get(item_id, user_id)
        if item is None:
            raise ValueError("Action item not found.")
        if item.status != "pending":
            raise ValueError(f"Action item already {item.status}.")

        task = await self.task_repo.create(
            user_id=user_id,
            title=item.detected_title,
            priority=item.detected_priority,
            estimated_minutes=item.detected_estimated_minutes,
            source="slack",
            raw_input=item.source_text,
        )
        item.status = "confirmed"
        item.created_task_id = task.id
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def reject(self, user_id: uuid.UUID, item_id: uuid.UUID) -> bool:
        item = await self.item_repo.get(item_id, user_id)
        if item is None or item.status != "pending":
            return False
        item.status = "rejected"
        await self.db.flush()
        return True


def _safe_int(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))
