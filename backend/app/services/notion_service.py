"""
Notion integration service.

RULE: Candidate tasks read from Notion NEVER become Tasks automatically. scan_database() only
      creates pending NotionImportItem rows; import_item() is the single approval-gated path that
      creates a Task. Framed as import/dismiss (not detect/confirm) because Notion rows are already
      structured tasks — no LLM detection, just structured extraction + explicit user import.

Structure the user already built in Notion (sub-items, "Blocked by") is kept: a scan records the page
ids, and each import links the new task to whatever the other side already became (TIME-326).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.notion_source import NotionTaskSource
from app.integrations.task_source_base import TaskSourceProvider
from app.llm.gateway import LLMGateway
from app.models.notion import NotionImportItem, NotionIntegration
from app.models.task import Task
from app.repositories.notion_repository import (
    NotionImportItemRepository,
    NotionIntegrationRepository,
)
from app.repositories.task_repository import TaskRepository
from app.services.prerequisite_service import PrerequisiteService
from app.services.step_service import StepError, StepService
from app.services.step_suggestion_service import StepSuggestionService
from app.services.task_autoschedule import autoschedule_task

_PROVIDERS: dict[str, TaskSourceProvider] = {
    "notion": NotionTaskSource(),
}


class NotionNotConnected(Exception):
    """Raised when scanning is attempted without an active Notion integration."""


@dataclass
class PendingItem:
    """A pending import, with what TimeSense knows about the Notion page it is a sub-item of."""

    item: NotionImportItem
    parent_title_hint: str | None = None
    # Set while that parent page is itself still waiting to be imported, so the app can offer
    # "Import both".
    parent_pending_item_id: uuid.UUID | None = None


class NotionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.integration_repo = NotionIntegrationRepository(db)
        self.item_repo = NotionImportItemRepository(db)
        self.task_repo = TaskRepository(db)
        self.steps = StepService(db)
        self.prerequisites = PrerequisiteService(db)

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
                external_parent_id=candidate.parent_external_id,
                external_prereq_ids=candidate.prerequisite_external_ids,
            )
            items.append(item)
        return len(candidates), items

    # ── Approval gate (import / dismiss) ──────────────────────────────────────

    async def list_pending(self, user_id: uuid.UUID) -> list[NotionImportItem]:
        return await self.item_repo.list_pending(user_id)

    async def list_pending_with_parents(self, user_id: uuid.UUID) -> list[PendingItem]:
        """Pending items, each with the title of the Notion page it is a sub-item of, when that page is
        known here (TIME-326). A parent that was dismissed is treated as unknown."""
        items = await self.item_repo.list_pending(user_id)
        parents = await self.item_repo.by_pages(
            user_id, (i.external_parent_id for i in items if i.external_parent_id)
        )
        pending: list[PendingItem] = []
        for item in items:
            parent = parents.get(item.external_parent_id) if item.external_parent_id else None
            if parent is None or parent.status == "dismissed":
                pending.append(PendingItem(item))
                continue
            pending.append(PendingItem(
                item,
                parent_title_hint=parent.title,
                parent_pending_item_id=parent.id if parent.status == "pending" else None,
            ))
        return pending

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
        item.status = "imported"
        item.created_task_id = task.id
        await self.db.flush()
        # Link it into the structure first, so placement below already knows what it waits for.
        await self._link(user_id, item, task)
        # Plan it in like a capture — estimate a duration and place it in an open slot (around
        # meetings + tasks). Leaves it untimed if the day is full (TIME-278).
        await autoschedule_task(self.db, task)
        await self.db.refresh(item)
        return item

    async def dismiss(self, user_id: uuid.UUID, item_id: uuid.UUID) -> bool:
        item = await self.item_repo.get(item_id, user_id)
        if item is None or item.status != "pending":
            return False
        item.status = "dismissed"
        await self.db.flush()
        return True

    async def suggest_parent(
        self, user_id: uuid.UUID, task: Task, gateway: LLMGateway
    ) -> Task | None:
        """An open task that an imported task with no Notion parent looks like part of. Offered to the
        user and never applied, as with capture (TIME-326)."""
        if task.parent_task_id is not None:
            return None
        open_tasks = [
            (task_id, title) for task_id, title in await self.task_repo.open_tasks_for_matching(user_id)
            if task_id != task.id
        ]
        match = await StepSuggestionService(gateway).suggest_parent(task.title, open_tasks)
        return await self.task_repo.get_by_id(match, user_id) if match is not None else None

    # ── Relations (TIME-326) ──────────────────────────────────────────────────

    async def _link(self, user_id: uuid.UUID, item: NotionImportItem, task: Task) -> None:
        """Rebuild the Notion structure around a newly imported task, in both directions.

        Notion allows more than TimeSense does (sub-items of sub-items, loops of dependencies). A link
        that breaks one of TimeSense's rules is skipped rather than failing the import: the task itself
        is what the user asked for."""
        pages = set(item.external_prereq_ids or [])
        if item.external_parent_id:
            pages.add(item.external_parent_id)
        known = await self.item_repo.by_pages(user_id, pages)

        # The page it is a sub-item of, if that page was imported first.
        if item.external_parent_id:
            parent = await self._task_of(user_id, known.get(item.external_parent_id))
            if parent is not None:
                await _unless_refused(self.steps.attach(task, parent))

        # Its own sub-items that were imported before it.
        for child_item in await self.item_repo.children_of(user_id, item.page_id):
            child = await self._task_of(user_id, child_item)
            if child is not None and child.parent_task_id is None:
                await _unless_refused(self.steps.attach(child, task))

        # What it is blocked by, and what was already waiting on it.
        for page_id in item.external_prereq_ids or []:
            prerequisite = await self._task_of(user_id, known.get(page_id))
            if prerequisite is not None:
                await _unless_refused(self.prerequisites.add(user_id, task.id, prerequisite.id))
        for waiting_item in await self.item_repo.waiting_on(user_id, item.page_id):
            waiting = await self._task_of(user_id, waiting_item)
            if waiting is not None:
                await _unless_refused(self.prerequisites.add(user_id, waiting.id, task.id))

    async def _task_of(self, user_id: uuid.UUID, other: NotionImportItem | None) -> Task | None:
        """The task an import item became, if it has been imported."""
        if other is None or other.status != "imported" or other.created_task_id is None:
            return None
        return await self.task_repo.get_by_id(other.created_task_id, user_id)


async def _unless_refused(operation) -> None:
    try:
        await operation
    except StepError:
        pass
