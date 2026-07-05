from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.slack import SlackActionItem, SlackIntegration


class SlackIntegrationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active(self, user_id: uuid.UUID) -> SlackIntegration | None:
        result = await self.db.execute(
            select(SlackIntegration).where(
                SlackIntegration.user_id == user_id,
                SlackIntegration.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self, user_id: uuid.UUID, access_token: str, team_id: str | None = None
    ) -> SlackIntegration:
        existing = await self.get_active(user_id)
        if existing:
            existing.access_token = access_token
            existing.team_id = team_id
            await self.db.flush()
            return existing
        integration = SlackIntegration(
            user_id=user_id, access_token=access_token, team_id=team_id
        )
        self.db.add(integration)
        await self.db.flush()
        return integration

    async def deactivate(self, user_id: uuid.UUID) -> bool:
        integration = await self.get_active(user_id)
        if integration is None:
            return False
        integration.is_active = False
        await self.db.flush()
        return True


class SlackActionItemRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        channel: str,
        message_ts: str,
        source_text: str,
        detected_title: str,
        detected_priority: int,
        detected_estimated_minutes: int | None,
    ) -> SlackActionItem:
        item = SlackActionItem(
            user_id=user_id,
            channel=channel,
            message_ts=message_ts,
            source_text=source_text,
            detected_title=detected_title,
            detected_priority=detected_priority,
            detected_estimated_minutes=detected_estimated_minutes,
        )
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def get(self, item_id: uuid.UUID, user_id: uuid.UUID) -> SlackActionItem | None:
        result = await self.db.execute(
            select(SlackActionItem).where(
                SlackActionItem.id == item_id, SlackActionItem.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_pending(self, user_id: uuid.UUID) -> list[SlackActionItem]:
        result = await self.db.execute(
            select(SlackActionItem)
            .where(SlackActionItem.user_id == user_id, SlackActionItem.status == "pending")
            .order_by(SlackActionItem.created_at.desc())
        )
        return list(result.scalars().all())

    async def exists_for_message(self, user_id: uuid.UUID, message_ts: str) -> bool:
        """Avoid creating a duplicate pending item if the same message is scanned twice."""
        result = await self.db.execute(
            select(SlackActionItem.id).where(
                SlackActionItem.user_id == user_id,
                SlackActionItem.message_ts == message_ts,
            )
        )
        return result.first() is not None
