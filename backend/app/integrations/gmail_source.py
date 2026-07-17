"""
Gmail email source (read-only).

Fetches recent unread inbox messages via the Gmail REST API using `format=metadata`, so only headers
(Subject/From) + Gmail's short `snippet` come back — the message body is never requested or stored.
Query mirrors "recent inbox, read-only": `in:inbox is:unread newer_than:30d`.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status

from app.integrations.email_source_base import EmailMessage, EmailSourceProvider

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
# Recent unread inbox mail. Scoped to the inbox and last 30 days (privacy + noise) but NOT to the
# Primary tab — many users keep unread mail in other tabs, and category:primary silently matched
# nothing for them (the "no recent unread emails" bug, TIME-244).
_QUERY = "in:inbox is:unread newer_than:30d"


class GmailEmailSource(EmailSourceProvider):
    """Reads recent unread Primary emails via the Gmail REST API (metadata + snippet only)."""

    @property
    def name(self) -> str:
        return "gmail"

    async def list_recent_emails(self, access_token: str, max_results: int = 25) -> list[EmailMessage]:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            listing = await client.get(
                f"{GMAIL_API}/messages",
                headers=headers,
                params={"q": _QUERY, "maxResults": min(max_results, 50)},
            )
            _raise_for(listing)
            ids = [m["id"] for m in listing.json().get("messages", [])]

            out: list[EmailMessage] = []
            for mid in ids:
                # format=metadata → headers + snippet, NEVER the body.
                resp = await client.get(
                    f"{GMAIL_API}/messages/{mid}",
                    headers=headers,
                    params=[("format", "metadata"),
                            ("metadataHeaders", "Subject"), ("metadataHeaders", "From")],
                )
                _raise_for(resp)
                out.append(_to_email(resp.json()))
            return out


def _raise_for(resp: httpx.Response) -> None:
    if resp.status_code == 401:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gmail token expired.")
    if not resp.is_success:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Gmail API error.")


def _to_email(body: dict) -> EmailMessage:
    headers = {h["name"].lower(): h["value"] for h in body.get("payload", {}).get("headers", [])}
    received = None
    if body.get("internalDate"):
        try:
            received = datetime.fromtimestamp(int(body["internalDate"]) / 1000, tz=timezone.utc)
        except (ValueError, TypeError):
            received = None
    return EmailMessage(
        message_id=body["id"],
        thread_id=body.get("threadId"),
        subject=headers.get("subject", "(no subject)"),
        sender=headers.get("from"),
        snippet=body.get("snippet", ""),
        received_at=received,
    )
