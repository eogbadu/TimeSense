"""
Slack OAuth 2.0 (v2) handshake.

Slack's scan→task flow is already built (TIME-049); this adds the missing consent handshake so a
user can connect without pasting a token. Slack's token exchange returns 200 even on failure with
`{"ok": false, ...}`, so we check `ok` explicitly. Bot tokens don't expire (no refresh/expiry).
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.config import settings

AUTHORIZE_ENDPOINT = "https://slack.com/oauth/v2/authorize"
TOKEN_ENDPOINT = "https://slack.com/api/oauth.v2.access"
# Bot scopes needed to read channel messages for action-item detection.
SCOPES = "channels:history,channels:read,groups:history"


class SlackOAuthError(Exception):
    """Slack returned ok:false (or an unexpected payload) during the token exchange."""


@dataclass
class SlackTokenResult:
    access_token: str
    team_id: str | None


def is_configured() -> bool:
    return bool(settings.slack_client_id and settings.slack_client_secret)


def build_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.slack_client_id,
        "scope": SCOPES,
        "redirect_uri": settings.slack_redirect_uri,
        "state": state,
    }
    return f"{AUTHORIZE_ENDPOINT}?{urlencode(params)}"


async def exchange_code(code: str) -> SlackTokenResult:
    data = {
        "code": code,
        "client_id": settings.slack_client_id,
        "client_secret": settings.slack_client_secret,
        "redirect_uri": settings.slack_redirect_uri,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(TOKEN_ENDPOINT, data=data)
        resp.raise_for_status()
        body = resp.json()
    if not body.get("ok"):
        raise SlackOAuthError(body.get("error", "slack_oauth_failed"))
    return SlackTokenResult(
        access_token=body["access_token"],
        team_id=(body.get("team") or {}).get("id"),
    )
