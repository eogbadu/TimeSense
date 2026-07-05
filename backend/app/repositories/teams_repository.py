from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.teams import TeamsActionItem, TeamsIntegration


class TeamsIntegrationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active(self, user_id: uuid.UUID) -> TeamsIntegration | None:
        result = await self.db.execute(
            select(TeamsIntegration).where(
                TeamsIntegration.user_id == user_id,
                TeamsIntegration.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self, user_id: uuid.UUID, access_token: str, tenant_id: str | None = None
    ) -> TeamsIntegration:
        existing = await self.get_active(user_id)
        if existing:
            existing.access_token = access_token
            existing.tenant_id = tenant_id
            await self.db.flush()
            return existing
        integration = TeamsIntegration(
            user_id=user_id, access_token=access_token, tenant_id=tenant_id
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


class TeamsActionItemRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        conversation_id: str,
        message_id: str,
        source_text: str,
        detected_title: str,
        detected_priority: int,
        detected_estimated_minutes: int | None,
    ) -> TeamsActionItem:
        item = TeamsActionItem(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            source_text=source_text,
            detected_title=detected_title,
            detected_priority=detected_priority,
            detected_estimated_minutes=detected_estimated_minutes,
        )
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def get(self, item_id: uuid.UUID, user_id: uuid.UUID) -> TeamsActionItem | None:
        result = await self.db.execute(
            select(TeamsActionItem).where(
                TeamsActionItem.id == item_id, TeamsActionItem.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_pending(self, user_id: uuid.UUID) -> list[TeamsActionItem]:
        result = await self.db.execute(
            select(TeamsActionItem)
            .where(TeamsActionItem.user_id == user_id, TeamsActionItem.status == "pending")
            .order_by(TeamsActionItem.created_at.desc())
        )
        return list(result.scalars().all())

    async def exists_for_message(self, user_id: uuid.UUID, message_id: str) -> bool:
        """Avoid creating a duplicate pending item if the same message is scanned twice."""
        result = await self.db.execute(
            select(TeamsActionItem.id).where(
                TeamsActionItem.user_id == user_id,
                TeamsActionItem.message_id == message_id,
            )
        )
        return result.first() is not None
