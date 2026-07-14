"""
Gmail OAuth 2.0 handshake for READ-ONLY email access (task detection).

Same server-side token-exchange pattern as google_oauth (Calendar): `build_authorize_url` produces the
consent URL; `exchange_code` swaps the code for tokens; `refresh_access_token` mints a fresh access
token from the stored refresh token (used before an on-demand scan when the current one has expired).

Reuses the same Google OAuth *app* (google_client_id/secret) but requests only the gmail.readonly
scope and its own redirect URI, so connecting Gmail never asks for calendar consent (and vice-versa).
We never request send/modify scopes — read-only, always.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx

from app.core.config import settings

AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
# Read-only Gmail; openid/email to identify the account. No send/modify scopes, ever.
SCOPES = "openid email https://www.googleapis.com/auth/gmail.readonly"


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
        "redirect_uri": settings.gmail_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "access_type": "offline",     # ask for a refresh token
        "prompt": "consent",          # ensure a refresh token is returned on re-consent
        "include_granted_scopes": "true",
    }
    return f"{AUTHORIZE_ENDPOINT}?{urlencode(params)}"


def _to_token_result(body: dict, fallback_refresh: str | None = None) -> TokenResult:
    expires_at = None
    if body.get("expires_in"):
        expires_at = datetime.now(UTC) + timedelta(seconds=int(body["expires_in"]))
    # A refresh grant doesn't return a new refresh_token — keep the existing one.
    return TokenResult(
        access_token=body["access_token"],
        refresh_token=body.get("refresh_token") or fallback_refresh,
        expires_at=expires_at,
    )


async def exchange_code(code: str) -> TokenResult:
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.gmail_redirect_uri,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(TOKEN_ENDPOINT, data=data)
        resp.raise_for_status()
        body = resp.json()
    return _to_token_result(body)


async def refresh_access_token(refresh_token: str) -> TokenResult:
    """Mint a fresh access token from a stored refresh token. The response keeps the same refresh
    token (Google doesn't re-issue one), so we carry it forward."""
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
    return _to_token_result(body, fallback_refresh=refresh_token)
