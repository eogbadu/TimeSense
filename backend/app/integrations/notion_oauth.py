"""
Notion OAuth 2.0 handshake.

Notion's page→candidate-task import is already built (TIME-051); this adds the missing consent
handshake so a user can connect without pasting an internal-integration token. The token endpoint
uses HTTP Basic auth (client_id:client_secret) with a JSON body, and returns a workspace-scoped
access token that does not expire (no refresh).
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.config import settings

AUTHORIZE_ENDPOINT = "https://api.notion.com/v1/oauth/authorize"
TOKEN_ENDPOINT = "https://api.notion.com/v1/oauth/token"


class NotionOAuthError(Exception):
    """Notion returned an error (or no access_token) during the token exchange."""


@dataclass
class NotionTokenResult:
    access_token: str
    workspace_id: str | None


def is_configured() -> bool:
    return bool(settings.notion_client_id and settings.notion_client_secret)


def build_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.notion_client_id,
        "redirect_uri": settings.notion_redirect_uri,
        "response_type": "code",
        "owner": "user",
        "state": state,
    }
    return f"{AUTHORIZE_ENDPOINT}?{urlencode(params)}"


async def exchange_code(code: str) -> NotionTokenResult:
    body = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.notion_redirect_uri,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            TOKEN_ENDPOINT,
            json=body,
            auth=(settings.notion_client_id, settings.notion_client_secret),  # HTTP Basic
        )
        resp.raise_for_status()
        data = resp.json()
    token = data.get("access_token")
    if not token:
        raise NotionOAuthError(data.get("error", "notion_oauth_failed"))
    return NotionTokenResult(access_token=token, workspace_id=data.get("workspace_id"))
