from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notion import NotionImportItem, NotionIntegration


class NotionIntegrationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active(self, user_id: uuid.UUID) -> NotionIntegration | None:
        result = await self.db.execute(
            select(NotionIntegration).where(
                NotionIntegration.user_id == user_id,
                NotionIntegration.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self, user_id: uuid.UUID, access_token: str, workspace_id: str | None = None
    ) -> NotionIntegration:
        existing = await self.get_active(user_id)
        if existing:
            existing.access_token = access_token
            existing.workspace_id = workspace_id
            await self.db.flush()
            return existing
        integration = NotionIntegration(
            user_id=user_id, access_token=access_token, workspace_id=workspace_id
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


class NotionImportItemRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        database_id: str,
        page_id: str,
        title: str,
        notes: str | None,
        due_at: datetime | None,
    ) -> NotionImportItem:
        item = NotionImportItem(
            user_id=user_id,
            database_id=database_id,
            page_id=page_id,
            title=title,
            notes=notes,
            due_at=due_at,
        )
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def get(self, item_id: uuid.UUID, user_id: uuid.UUID) -> NotionImportItem | None:
        result = await self.db.execute(
            select(NotionImportItem).where(
                NotionImportItem.id == item_id, NotionImportItem.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_pending(self, user_id: uuid.UUID) -> list[NotionImportItem]:
        result = await self.db.execute(
            select(NotionImportItem)
            .where(NotionImportItem.user_id == user_id, NotionImportItem.status == "pending")
            .order_by(NotionImportItem.created_at.desc())
        )
        return list(result.scalars().all())

    async def exists_for_page(self, user_id: uuid.UUID, page_id: str) -> bool:
        """Avoid creating a duplicate import item if the same page is scanned twice."""
        result = await self.db.execute(
            select(NotionImportItem.id).where(
                NotionImportItem.user_id == user_id,
                NotionImportItem.page_id == page_id,
            )
        )
        return result.first() is not None
