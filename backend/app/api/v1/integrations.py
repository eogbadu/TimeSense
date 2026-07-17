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
from app.core.security import CurrentUser
from app.core.oauth_state import (
    OAuthStateError,
    decode_state,
    platform_from_state,
    sign_state,
)
from app.integrations import (
    gmail_oauth,
    google_oauth,
    microsoft_oauth,
    notion_oauth,
    slack_oauth,
)
from app.integrations.notion_oauth import NotionOAuthError
from app.integrations.slack_oauth import SlackOAuthError
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.services.calendar_service import CalendarService
from app.repositories.calendar_repository import CalendarIntegrationRepository
from app.repositories.email_repository import EmailIntegrationRepository
from app.repositories.notion_repository import NotionIntegrationRepository
from app.repositories.slack_repository import SlackIntegrationRepository
from app.services.email_service import EmailService
from app.services.notion_service import NotionService
from app.services.slack_service import SlackService
from app.services.user_service import UserService

router = APIRouter(prefix="/integrations", tags=["integrations"])


class AuthorizeResponse(BaseModel):
    authorize_url: str


class IntegrationsStatus(BaseModel):
    """Which providers the user currently has an active connection to (drives Connect vs Disconnect)."""
    google: bool
    microsoft: bool
    gmail: bool
    slack: bool
    notion: bool


@router.get("/status", response_model=IntegrationsStatus)
async def integrations_status(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> IntegrationsStatus:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    cal = CalendarIntegrationRepository(db)
    return IntegrationsStatus(
        google=await cal.get_active(user.id, "google") is not None,
        microsoft=await cal.get_active(user.id, "microsoft") is not None,
        gmail=await EmailIntegrationRepository(db).get_active(user.id) is not None,
        slack=await SlackIntegrationRepository(db).get_active(user.id) is not None,
        notion=await NotionIntegrationRepository(db).get_active(user.id) is not None,
    )


def _redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


def _success(platform: str, provider: str) -> RedirectResponse:
    """Return to the client that started the flow: the web companion (platform=web) or the app."""
    if platform == "web":
        base = settings.oauth_web_success_redirect
        sep = "&" if "?" in base else "?"
        return _redirect(f"{base}{sep}provider={provider}")
    return _redirect(settings.oauth_success_redirect)


def _failure(platform: str = "mobile") -> RedirectResponse:
    if platform == "web":
        return _redirect(settings.oauth_web_failure_redirect)
    return _redirect(settings.oauth_failure_redirect)


async def _authorize(
    provider: str, oauth_mod, current_user, db: AsyncSession, platform: str = "mobile"
) -> AuthorizeResponse:
    if not oauth_mod.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{provider.capitalize()} Calendar isn't configured on the server yet.",
        )
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    state = sign_state(str(user.id), provider, platform=platform)
    return AuthorizeResponse(authorize_url=oauth_mod.build_authorize_url(state))


async def _callback(
    provider: str, oauth_mod, code: str | None, state: str | None, error: str | None, db: AsyncSession
) -> RedirectResponse:
    """Shared calendar OAuth callback: verify state → exchange code → store tokens → return to the
    originating client (mobile deep link or the web app, per the state's platform)."""
    if error or not code:
        return _failure(platform_from_state(state))
    try:
        st = decode_state(state or "", provider)
    except OAuthStateError:
        return _failure(platform_from_state(state))
    try:
        tokens = await oauth_mod.exchange_code(code)
    except (httpx.HTTPError, KeyError):
        return _failure(st.platform)

    await CalendarService(db).connect(
        user_id=uuid.UUID(st.user_id),
        provider=provider,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_expires_at=tokens.expires_at,
    )
    await db.commit()
    return _success(st.platform, provider)


@router.get("/google/authorize", response_model=AuthorizeResponse)
async def google_authorize(
    current_user: PremiumUser, db: AsyncSession = Depends(get_db), platform: str = "mobile"
):
    """Return the Google consent URL to open. Premium only. platform=web returns to the web app."""
    return await _authorize("google", google_oauth, current_user, db, platform)


@router.get("/google/callback")
async def google_callback(
    code: str | None = None, state: str | None = None, error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Google redirects here after consent."""
    return await _callback("google", google_oauth, code, state, error, db)


@router.get("/microsoft/authorize", response_model=AuthorizeResponse)
async def microsoft_authorize(
    current_user: PremiumUser, db: AsyncSession = Depends(get_db), platform: str = "mobile"
):
    """Return the Microsoft/Outlook consent URL to open. Premium only."""
    return await _authorize("microsoft", microsoft_oauth, current_user, db, platform)


@router.get("/microsoft/callback")
async def microsoft_callback(
    code: str | None = None, state: str | None = None, error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Microsoft redirects here after consent."""
    return await _callback("microsoft", microsoft_oauth, code, state, error, db)


@router.get("/gmail/authorize", response_model=AuthorizeResponse)
async def gmail_authorize(
    current_user: PremiumUser, db: AsyncSession = Depends(get_db), platform: str = "mobile"
):
    """Return the Gmail (read-only) consent URL to open. Premium only."""
    if not gmail_oauth.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gmail isn't configured on the server yet.",
        )
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    state = sign_state(str(user.id), "gmail", platform=platform)
    return AuthorizeResponse(authorize_url=gmail_oauth.build_authorize_url(state))


@router.get("/gmail/callback")
async def gmail_callback(
    code: str | None = None, state: str | None = None, error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Gmail redirects here after consent. Exchange the code, store the tokens via EmailService."""
    if error or not code:
        return _failure(platform_from_state(state))
    try:
        st = decode_state(state or "", "gmail")
    except OAuthStateError:
        return _failure(platform_from_state(state))
    try:
        tokens = await gmail_oauth.exchange_code(code)
    except (httpx.HTTPError, KeyError):
        return _failure(st.platform)

    await EmailService(db).connect(
        user_id=uuid.UUID(st.user_id), provider="gmail",
        access_token=tokens.access_token, refresh_token=tokens.refresh_token,
        token_expires_at=tokens.expires_at,
    )
    await db.commit()
    return _success(st.platform, "gmail")


@router.get("/notion/authorize", response_model=AuthorizeResponse)
async def notion_authorize(
    current_user: PremiumUser, db: AsyncSession = Depends(get_db), platform: str = "mobile"
):
    """Return the Notion consent URL to open. Premium only."""
    return await _authorize("notion", notion_oauth, current_user, db, platform)


@router.get("/notion/callback")
async def notion_callback(
    code: str | None = None, state: str | None = None, error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Notion redirects here after consent. Exchange the code, store the token via NotionService."""
    if error or not code:
        return _failure(platform_from_state(state))
    try:
        st = decode_state(state or "", "notion")
    except OAuthStateError:
        return _failure(platform_from_state(state))
    try:
        tokens = await notion_oauth.exchange_code(code)
    except (httpx.HTTPError, KeyError, NotionOAuthError):
        return _failure(st.platform)

    await NotionService(db).connect(uuid.UUID(st.user_id), tokens.access_token, tokens.workspace_id)
    await db.commit()
    return _success(st.platform, "notion")


@router.get("/slack/authorize", response_model=AuthorizeResponse)
async def slack_authorize(
    current_user: PremiumUser, db: AsyncSession = Depends(get_db), platform: str = "mobile"
):
    """Return the Slack consent URL to open. Premium only."""
    return await _authorize("slack", slack_oauth, current_user, db, platform)


@router.get("/slack/callback")
async def slack_callback(
    code: str | None = None, state: str | None = None, error: str | None = None,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
):
    """Slack redirects here after consent. Exchange the code, store the token via SlackService."""
    if error or not code:
        return _failure(platform_from_state(state))
    try:
        st = decode_state(state or "", "slack")
    except OAuthStateError:
        return _failure(platform_from_state(state))
    try:
        tokens = await slack_oauth.exchange_code(code)
    except (httpx.HTTPError, KeyError, SlackOAuthError):
        return _failure(st.platform)

    await SlackService(db, gateway).connect(uuid.UUID(st.user_id), tokens.access_token, tokens.team_id)
    await db.commit()
    return _success(st.platform, "slack")
