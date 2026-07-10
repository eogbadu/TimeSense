"""
OAuth handshake endpoints for third-party integrations.

Flow (server-side token exchange — the client secret never touches the device):
  1. Authenticated client calls GET /integrations/{provider}/authorize → we return the provider's
     consent URL carrying a signed `state` (identifies the user + CSRF).
  2. Client opens that URL; after consent the provider redirects the browser to
     GET /integrations/{provider}/callback?code=&state= (unauthenticated).
  3. We verify `state`, exchange `code` for tokens, store them encrypted via CalendarService.connect,
     then deep-link back into the app.

Google Calendar is the first provider; Microsoft/Outlook and Slack reuse the same pattern.
"""
from __future__ import annotations

import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.entitlements import PremiumUser
from app.core.oauth_state import OAuthStateError, sign_state, verify_state
from app.integrations import google_oauth
from app.services.calendar_service import CalendarService
from app.services.user_service import UserService

router = APIRouter(prefix="/integrations", tags=["integrations"])


class AuthorizeResponse(BaseModel):
    authorize_url: str


@router.get("/google/authorize", response_model=AuthorizeResponse)
async def google_authorize(current_user: PremiumUser, db: AsyncSession = Depends(get_db)):
    """Return the Google consent URL to open. Premium only."""
    if not google_oauth.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Calendar isn't configured on the server yet.",
        )
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    state = sign_state(str(user.id), "google")
    return AuthorizeResponse(authorize_url=google_oauth.build_authorize_url(state))


@router.get("/google/callback")
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Google redirects here after consent. Exchange the code, store tokens, deep-link back."""
    if error or not code:
        return RedirectResponse(settings.oauth_failure_redirect, status_code=status.HTTP_302_FOUND)

    try:
        user_id = verify_state(state or "", "google")
    except OAuthStateError:
        return RedirectResponse(settings.oauth_failure_redirect, status_code=status.HTTP_302_FOUND)

    try:
        tokens = await google_oauth.exchange_code(code)
    except (httpx.HTTPError, KeyError):
        return RedirectResponse(settings.oauth_failure_redirect, status_code=status.HTTP_302_FOUND)

    svc = CalendarService(db)
    await svc.connect(
        user_id=uuid.UUID(user_id),
        provider="google",
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_expires_at=tokens.expires_at,
    )
    await db.commit()
    return RedirectResponse(settings.oauth_success_redirect, status_code=status.HTTP_302_FOUND)
