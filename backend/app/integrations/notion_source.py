from datetime import datetime

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.integrations.task_source_base import SourceTask, TaskSourceProvider

NOTION_API = "https://api.notion.com/v1"


class NotionTaskSource(TaskSourceProvider):
    """Reads candidate tasks from a Notion database's pages via the Notion API."""

    @property
    def name(self) -> str:
        return "notion"

    async def list_candidate_tasks(
        self,
        access_token: str,
        source_id: str,
        limit: int = 50,
    ) -> list[SourceTask]:
        # `source_id` is the Notion database id.
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{NOTION_API}/databases/{source_id}/query",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Notion-Version": settings.notion_version,
                    "Content-Type": "application/json",
                },
                json={"page_size": min(limit, 100)},
            )
        if resp.status_code == 401:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Notion token expired.")
        if not resp.is_success:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Notion API error.")

        tasks: list[SourceTask] = []
        for page in resp.json().get("results", []):
            props = page.get("properties", {})
            title = _extract_title(props)
            if not title:
                continue  # skip untitled rows
            parent_id, blocked_by = _extract_relations(props)
            tasks.append(
                SourceTask(
                    external_id=page.get("id", ""),
                    title=title,
                    due=_extract_due(props),
                    parent_external_id=parent_id,
                    prerequisite_external_ids=blocked_by,
                )
            )
        return tasks


# The names Notion gives the relations its "Sub-items" and "Dependencies" features create, plus the
# obvious renames. Only relation properties are considered, so a text column called "Parent" is ignored.
_PARENT_NAMES = {"parent item", "parent", "parent task"}
_BLOCKED_BY_NAMES = {"blocked by", "depends on", "waiting on"}


def _extract_relations(properties: dict) -> tuple[str | None, list[str]]:
    """The page this row is a sub-item of, and the pages it is blocked by (TIME-326). A database
    without those relations gives (None, [])."""
    parent_id: str | None = None
    blocked_by: list[str] = []
    for name, prop in properties.items():
        if prop.get("type") != "relation":
            continue
        ids = [r.get("id") for r in prop.get("relation", []) if r.get("id")]
        key = name.strip().casefold()
        if key in _PARENT_NAMES and ids and parent_id is None:
            parent_id = ids[0]
        elif key in _BLOCKED_BY_NAMES:
            blocked_by.extend(i for i in ids if i not in blocked_by)
    return parent_id, blocked_by


def _extract_title(properties: dict) -> str:
    """Notion's title lives in the (single) property whose type is 'title'."""
    for prop in properties.values():
        if prop.get("type") == "title":
            parts = [t.get("plain_text", "") for t in prop.get("title", [])]
            return "".join(parts).strip()
    return ""


def _extract_due(properties: dict) -> datetime | None:
    """Use the first date-type property that has a start value."""
    for prop in properties.values():
        if prop.get("type") == "date":
            date_obj = prop.get("date")
            if date_obj and date_obj.get("start"):
                return _parse_notion_date(date_obj["start"])
    return None


def _parse_notion_date(raw: str) -> datetime | None:
    # Notion dates are ISO — either a date ("2026-07-10") or a datetime with offset.
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
