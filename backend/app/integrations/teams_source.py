import re
from datetime import datetime

import httpx
from fastapi import HTTPException, status

from app.integrations.message_source_base import MessageSourceProvider, SourceMessage

GRAPH_API = "https://graph.microsoft.com/v1.0"
_TAG_RE = re.compile(r"<[^>]+>")


class TeamsMessageSource(MessageSourceProvider):
    """Reads messages from a Microsoft Teams chat via Microsoft Graph."""

    @property
    def name(self) -> str:
        return "teams"

    async def list_recent_messages(
        self,
        access_token: str,
        channel: str,
        limit: int = 50,
    ) -> list[SourceMessage]:
        # `channel` carries the Teams chat/conversation id.
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GRAPH_API}/chats/{channel}/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"$top": min(limit, 50)},
            )
        if resp.status_code == 401:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Teams token expired.")
        if not resp.is_success:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Microsoft Graph error.")

        messages: list[SourceMessage] = []
        for item in resp.json().get("value", []):
            body = item.get("body", {})
            text = _to_plain_text(body.get("content", ""))
            if not text or item.get("messageType") != "message":
                continue  # skip system/event messages
            author = (item.get("from") or {}).get("user", {}).get("displayName")
            messages.append(
                SourceMessage(
                    message_id=item.get("id", ""),
                    channel=channel,
                    text=text,
                    author=author,
                    timestamp=_parse_graph_ts(item.get("createdDateTime")),
                )
            )
        return messages


def _to_plain_text(content: str) -> str:
    """Teams message bodies are often HTML; strip tags to plain text for the detector."""
    if not content:
        return ""
    return _TAG_RE.sub("", content).strip()


def _parse_graph_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
