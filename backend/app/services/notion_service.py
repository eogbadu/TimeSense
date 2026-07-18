"""
Notion integration service.

RULE: Candidate tasks read from Notion NEVER become Tasks automatically. scan_database() only
      creates pending NotionImportItem rows; import_item() is the single approval-gated path that
      creates a Task. Framed as import/dismiss (not detect/confirm) because Notion rows are already
      structured tasks — no LLM detection, just structured extraction + explicit user import.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.notion_source import NotionTaskSource
from app.integrations.task_source_base import TaskSourceProvider
from app.models.notion import NotionImportItem, NotionIntegration
from app.repositories.notion_repository import (
    NotionImportItemRepository,
    NotionIntegrationRepository,
)
from app.repositories.task_repository import TaskRepository
from app.services.task_autoschedule import autoschedule_task

_PROVIDERS: dict[str, TaskSourceProvider] = {
    "notion": NotionTaskSource(),
}


class NotionNotConnected(Exception):
    """Raised when scanning is attempted without an active Notion integration."""


class NotionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.integration_repo = NotionIntegrationRepository(db)
        self.item_repo = NotionImportItemRepository(db)
        self.task_repo = TaskRepository(db)

    # ── Token management ──────────────────────────────────────────────────────

    async def connect(
        self, user_id: uuid.UUID, access_token: str, workspace_id: str | None = None
    ) -> NotionIntegration:
        return await self.integration_repo.upsert(user_id, access_token, workspace_id)

    async def disconnect(self, user_id: uuid.UUID) -> bool:
        return await self.integration_repo.deactivate(user_id)

    # ── Scan (read candidate tasks — never creates Tasks) ─────────────────────

    async def scan_database(
        self, user_id: uuid.UUID, database_id: str, limit: int = 50
    ) -> tuple[int, list[NotionImportItem]]:
        integration = await self.integration_repo.get_active(user_id)
        if integration is None:
            raise NotionNotConnected("Notion is not connected.")

        provider = _PROVIDERS["notion"]
        candidates = await provider.list_candidate_tasks(
            access_token=integration.access_token, source_id=database_id, limit=limit
        )

        items: list[NotionImportItem] = []
        for candidate in candidates:
            if await self.item_repo.exists_for_page(user_id, candidate.external_id):
                continue
            item = await self.item_repo.create(
                user_id=user_id,
                database_id=database_id,
                page_id=candidate.external_id,
                title=candidate.title,
                notes=candidate.notes,
                due_at=candidate.due,
            )
            items.append(item)
        return len(candidates), items

    # ── Approval gate (import / dismiss) ──────────────────────────────────────

    async def list_pending(self, user_id: uuid.UUID) -> list[NotionImportItem]:
        return await self.item_repo.list_pending(user_id)

    async def import_item(self, user_id: uuid.UUID, item_id: uuid.UUID) -> NotionImportItem:
        """Create a real Task from a pending item. The only path that turns Notion into a Task.
        Raises ValueError if not found or already handled."""
        item = await self.item_repo.get(item_id, user_id)
        if item is None:
            raise ValueError("Import item not found.")
        if item.status != "pending":
            raise ValueError(f"Import item already {item.status}.")

        task = await self.task_repo.create(
            user_id=user_id,
            title=item.title,
            due_at=item.due_at,
            source="notion",
            raw_input=item.notes,
        )
        # Plan it in like a capture — estimate a duration and place it in an open slot (around
        # meetings + tasks). Leaves it untimed if the day is full (TIME-278).
        await autoschedule_task(self.db, task)
        item.status = "imported"
        item.created_task_id = task.id
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def dismiss(self, user_id: uuid.UUID, item_id: uuid.UUID) -> bool:
        item = await self.item_repo.get(item_id, user_id)
        if item is None or item.status != "pending":
            return False
        item.status = "dismissed"
        await self.db.flush()
        return True
