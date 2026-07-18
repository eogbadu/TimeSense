"""
Google OAuth 2.0 handshake for Calendar access.

`build_authorize_url` produces the consent URL the client opens; `exchange_code` swaps the returned
authorization code for tokens (server-side, so the client secret never leaves the backend). The
resulting tokens are handed to CalendarService.connect, which stores them encrypted at rest.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx

from app.core.config import settings

AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
# Read + write *events* (writes still gated behind in-app approval); openid/email to identify the account.
SCOPES = "openid email https://www.googleapis.com/auth/calendar.events"


@dataclass
class TokenResult:
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None


def is_configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


def build_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "access_type": "offline",     # ask for a refresh token
        "prompt": "consent",          # ensure a refresh token is returned on re-consent
        "include_granted_scopes": "true",
    }
    return f"{AUTHORIZE_ENDPOINT}?{urlencode(params)}"


async def exchange_code(code: str) -> TokenResult:
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
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
    """Exchange a stored refresh token for a fresh access token. Google usually doesn't return a new
    refresh token, so we keep the existing one."""
    data = {
        "refresh_token": refresh_token,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "grant_type": "refresh_token",
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
