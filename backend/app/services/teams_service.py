"""
Microsoft Teams integration service. Mirrors SlackService.

RULE: Detected action items NEVER become Tasks automatically. scan_conversation() only creates
      pending TeamsActionItem rows; confirm() is the single approval-gated path that creates a
      Task — same approval gate as the Slack and calendar-write flows.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.message_source_base import MessageSourceProvider
from app.integrations.teams_source import TeamsMessageSource
from app.llm.gateway import LLMGateway
from app.models.teams import TeamsActionItem, TeamsIntegration
from app.repositories.task_repository import TaskRepository
from app.repositories.teams_repository import (
    TeamsActionItemRepository,
    TeamsIntegrationRepository,
)
from app.services.action_item_detection import ActionItemDetectionService

_PROVIDERS: dict[str, MessageSourceProvider] = {
    "teams": TeamsMessageSource(),
}


class TeamsNotConnected(Exception):
    """Raised when scanning is attempted without an active Teams integration."""


class TeamsService:
    def __init__(self, db: AsyncSession, gateway: LLMGateway) -> None:
        self.db = db
        self.integration_repo = TeamsIntegrationRepository(db)
        self.item_repo = TeamsActionItemRepository(db)
        self.task_repo = TaskRepository(db)
        self.detector = ActionItemDetectionService(gateway)

    # ── Token management ──────────────────────────────────────────────────────

    async def connect(
        self, user_id: uuid.UUID, access_token: str, tenant_id: str | None = None
    ) -> TeamsIntegration:
        return await self.integration_repo.upsert(user_id, access_token, tenant_id)

    async def disconnect(self, user_id: uuid.UUID) -> bool:
        return await self.integration_repo.deactivate(user_id)

    # ── Scan (detect only — never creates Tasks) ──────────────────────────────

    async def scan_conversation(
        self, user_id: uuid.UUID, conversation_id: str, limit: int = 50
    ) -> tuple[int, list[TeamsActionItem]]:
        integration = await self.integration_repo.get_active(user_id)
        if integration is None:
            raise TeamsNotConnected("Teams is not connected.")

        provider = _PROVIDERS["teams"]
        messages = await provider.list_recent_messages(
            access_token=integration.access_token, channel=conversation_id, limit=limit
        )

        detected: list[TeamsActionItem] = []
        for message in messages:
            if await self.item_repo.exists_for_message(user_id, message.message_id):
                continue
            result = await self.detector.detect(message.text)
            if not result.is_action_item:
                continue
            item = await self.item_repo.create(
                user_id=user_id,
                conversation_id=message.channel,
                message_id=message.message_id,
                source_text=message.text,
                detected_title=result.title,
                detected_priority=result.priority,
                detected_estimated_minutes=result.estimated_minutes,
            )
            detected.append(item)
        return len(messages), detected

    # ── Approval gate ─────────────────────────────────────────────────────────

    async def list_pending(self, user_id: uuid.UUID) -> list[TeamsActionItem]:
        return await self.item_repo.list_pending(user_id)

    async def confirm(self, user_id: uuid.UUID, item_id: uuid.UUID) -> TeamsActionItem:
        """Create a real Task from a pending item. The only path that turns Teams into a Task.
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
            source="teams",
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
