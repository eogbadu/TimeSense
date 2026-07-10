"""
Signed, expiring OAuth `state` tokens.

The OAuth handshake starts on an authenticated request (we know the user) but the provider's
redirect hits `/callback` unauthenticated. We carry the user's identity across that hop in a signed,
short-lived `state` value — which also doubles as CSRF protection. HS256 over `settings.secret_key`.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings

_ALG = "HS256"
_TYP = "oauth_state"
DEFAULT_TTL_SECONDS = 600


class OAuthStateError(ValueError):
    """Raised when a state token is missing, tampered with, expired, or for the wrong provider."""


def sign_state(user_id: str, provider: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "provider": provider,
        "typ": _TYP,
        "iat": now,
        "exp": now + timedelta(seconds=ttl_seconds),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=_ALG)


def verify_state(token: str, expected_provider: str) -> str:
    """Return the user_id encoded in a valid state token, or raise OAuthStateError."""
    if not token:
        raise OAuthStateError("Missing state.")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_ALG])
    except jwt.ExpiredSignatureError as exc:
        raise OAuthStateError("State expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise OAuthStateError("Invalid state.") from exc
    if payload.get("typ") != _TYP:
        raise OAuthStateError("Wrong token type.")
    if payload.get("provider") != expected_provider:
        raise OAuthStateError("Provider mismatch.")
    sub = payload.get("sub")
    if not sub:
        raise OAuthStateError("State missing subject.")
    return sub
