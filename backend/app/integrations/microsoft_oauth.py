"""
Microsoft OAuth 2.0 handshake for Outlook Calendar (Microsoft Graph).

Same shape as google_oauth: build the consent URL, then exchange the code for tokens server-side.
Uses the common (multi-tenant) endpoint so both work and personal Microsoft accounts can connect.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx

from app.core.config import settings

AUTHORIZE_ENDPOINT = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
TOKEN_ENDPOINT = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
# offline_access → refresh token; Calendars.ReadWrite so writes work behind in-app approval.
SCOPES = "openid email offline_access https://graph.microsoft.com/Calendars.ReadWrite"


@dataclass
class TokenResult:
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None


def is_configured() -> bool:
    return bool(settings.microsoft_client_id and settings.microsoft_client_secret)


def build_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.microsoft_client_id,
        "redirect_uri": settings.microsoft_redirect_uri,
        "response_type": "code",
        "response_mode": "query",
        "scope": SCOPES,
        "state": state,
    }
    return f"{AUTHORIZE_ENDPOINT}?{urlencode(params)}"


async def exchange_code(code: str) -> TokenResult:
    data = {
        "code": code,
        "client_id": settings.microsoft_client_id,
        "client_secret": settings.microsoft_client_secret,
        "redirect_uri": settings.microsoft_redirect_uri,
        "grant_type": "authorization_code",
        "scope": SCOPES,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(TOKEN_ENDPOINT, data=data)
        resp.raise_for_status()
        body = resp.json()
    expires_at = None
    if body.get("expires_in"):
        expires_at = datetime.now(UTC) + timedelta(seconds=int(body["expires_in"]))
    return TokenResult(
        access_token=body["access_token"],
        refresh_token=body.get("refresh_token"),
        expires_at=expires_at,
    )


async def refresh_access_token(refresh_token: str) -> TokenResult:
    """Exchange a stored refresh token for a fresh access token (rotating refresh token when returned)."""
    data = {
        "refresh_token": refresh_token,
        "client_id": settings.microsoft_client_id,
        "client_secret": settings.microsoft_client_secret,
        "grant_type": "refresh_token",
        "scope": SCOPES,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(TOKEN_ENDPOINT, data=data)
        resp.raise_for_status()
        body = resp.json()
    expires_at = None
    if body.get("expires_in"):
        expires_at = datetime.now(UTC) + timedelta(seconds=int(body["expires_in"]))
    return TokenResult(
        access_token=body["access_token"],
        refresh_token=body.get("refresh_token") or refresh_token,
        expires_at=expires_at,
    )
