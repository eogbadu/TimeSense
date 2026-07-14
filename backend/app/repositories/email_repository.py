from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_integration import EmailActionItem, EmailIntegration


class EmailIntegrationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active(self, user_id: uuid.UUID) -> EmailIntegration | None:
        result = await self.db.execute(
            select(EmailIntegration).where(
                EmailIntegration.user_id == user_id,
                EmailIntegration.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: uuid.UUID,
        access_token: str,
        refresh_token: str | None = None,
        token_expires_at: datetime | None = None,
        provider: str = "gmail",
    ) -> EmailIntegration:
        existing = await self.get_active(user_id)
        if existing:
            existing.provider = provider
            existing.access_token = access_token
            # Only overwrite the refresh token when a new one is supplied (Google omits it on refresh).
            if refresh_token is not None:
                existing.refresh_token = refresh_token
            existing.token_expires_at = token_expires_at
            await self.db.flush()
            return existing
        integration = EmailIntegration(
            user_id=user_id, provider=provider, access_token=access_token,
            refresh_token=refresh_token, token_expires_at=token_expires_at,
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


class EmailActionItemRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        message_id: str,
        thread_id: str | None,
        subject: str,
        sender: str | None,
        source_text: str,
        detected_title: str,
        detected_priority: int,
        detected_estimated_minutes: int | None,
    ) -> EmailActionItem:
        item = EmailActionItem(
            user_id=user_id, message_id=message_id, thread_id=thread_id, subject=subject,
            sender=sender, source_text=source_text, detected_title=detected_title,
            detected_priority=detected_priority, detected_estimated_minutes=detected_estimated_minutes,
        )
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def get(self, item_id: uuid.UUID, user_id: uuid.UUID) -> EmailActionItem | None:
        result = await self.db.execute(
            select(EmailActionItem).where(
                EmailActionItem.id == item_id, EmailActionItem.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_pending(self, user_id: uuid.UUID) -> list[EmailActionItem]:
        result = await self.db.execute(
            select(EmailActionItem)
            .where(EmailActionItem.user_id == user_id, EmailActionItem.status == "pending")
            .order_by(EmailActionItem.created_at.desc())
        )
        return list(result.scalars().all())

    async def exists_for_message(self, user_id: uuid.UUID, message_id: str) -> bool:
        """Avoid a duplicate pending item if the same email is scanned twice."""
        result = await self.db.execute(
            select(EmailActionItem.id).where(
                EmailActionItem.user_id == user_id,
                EmailActionItem.message_id == message_id,
            )
        )
        return result.first() is not None
