from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status

from app.integrations.message_source_base import MessageSourceProvider, SourceMessage

SLACK_API = "https://slack.com/api"


class SlackMessageSource(MessageSourceProvider):
    """Reads messages from Slack via the conversations.history Web API."""

    @property
    def name(self) -> str:
        return "slack"

    async def list_recent_messages(
        self,
        access_token: str,
        channel: str,
        limit: int = 50,
    ) -> list[SourceMessage]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{SLACK_API}/conversations.history",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"channel": channel, "limit": min(limit, 200)},
            )
        if resp.status_code == 401:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Slack token expired.")
        if not resp.is_success:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Slack API error.")

        body = resp.json()
        # Slack returns 200 with {"ok": false, "error": "..."} on API-level failures.
        if not body.get("ok"):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Slack API error: {body.get('error', 'unknown')}",
            )

        messages: list[SourceMessage] = []
        for item in body.get("messages", []):
            text = item.get("text", "")
            if not text or item.get("subtype"):  # skip joins/system messages
                continue
            ts = item.get("ts", "")
            messages.append(
                SourceMessage(
                    message_id=ts,
                    channel=channel,
                    text=text,
                    author=item.get("user"),
                    timestamp=_parse_slack_ts(ts),
                )
            )
        return messages


def _parse_slack_ts(ts: str) -> datetime | None:
    """Slack message ts is a stringified unix epoch with microseconds, e.g. '1699900000.001200'."""
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except (ValueError, TypeError):
        return None
