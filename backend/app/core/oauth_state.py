"""
Signed, expiring OAuth `state` tokens.

The OAuth handshake starts on an authenticated request (we know the user) but the provider's
redirect hits `/callback` unauthenticated. We carry the user's identity across that hop in a signed,
short-lived `state` value — which also doubles as CSRF protection. HS256 over `settings.secret_key`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings

_ALG = "HS256"
_TYP = "oauth_state"
DEFAULT_TTL_SECONDS = 600
# Which client started the flow — decides where the callback redirects back to (mobile deep link vs
# the web app). Default mobile so existing native flows are unchanged.
_PLATFORMS = frozenset({"mobile", "web"})
_DEFAULT_PLATFORM = "mobile"


class OAuthStateError(ValueError):
    """Raised when a state token is missing, tampered with, expired, or for the wrong provider."""


@dataclass(frozen=True)
class OAuthState:
    user_id: str
    platform: str


def sign_state(
    user_id: str, provider: str, platform: str = _DEFAULT_PLATFORM,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "provider": provider,
        "platform": platform if platform in _PLATFORMS else _DEFAULT_PLATFORM,
        "typ": _TYP,
        "iat": now,
        "exp": now + timedelta(seconds=ttl_seconds),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=_ALG)


def decode_state(token: str, expected_provider: str) -> OAuthState:
    """Fully verify a state token → its user_id + originating platform, or raise OAuthStateError."""
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
    platform = payload.get("platform")
    return OAuthState(user_id=sub, platform=platform if platform in _PLATFORMS else _DEFAULT_PLATFORM)


def verify_state(token: str, expected_provider: str) -> str:
    """Return the user_id encoded in a valid state token, or raise OAuthStateError.
    (Back-compat wrapper around decode_state.)"""
    return decode_state(token, expected_provider).user_id


def platform_from_state(token: str | None) -> str:
    """Best-effort platform read for the *failure* redirect — where the state may be invalid/expired
    but the provider still echoed it back. Never raises; defaults to mobile."""
    if not token:
        return _DEFAULT_PLATFORM
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_ALG],
                             options={"verify_exp": False})
        platform = payload.get("platform")
        return platform if platform in _PLATFORMS else _DEFAULT_PLATFORM
    except jwt.InvalidTokenError:
        return _DEFAULT_PLATFORM
