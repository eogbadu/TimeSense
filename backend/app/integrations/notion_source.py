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
            tasks.append(
                SourceTask(
                    external_id=page.get("id", ""),
                    title=title,
                    due=_extract_due(props),
                )
            )
        return tasks


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
