"""
Email integration service (Gmail first).

RULE (same as Slack/calendar-writes): detected action items NEVER become Tasks automatically. This
first slice only handles the read-only OAuth connection; scanning + the approval-gated confirm() land
in TIME-215/216.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations import gmail_oauth
from app.integrations.email_source_base import EmailMessage, EmailSourceProvider
from app.integrations.gmail_source import GmailEmailSource
from app.models.email_integration import EmailIntegration
from app.repositories.email_repository import EmailIntegrationRepository

# Read-only mail sources, keyed by provider (mirrors SlackService._PROVIDERS).
_PROVIDERS: dict[str, EmailSourceProvider] = {
    "gmail": GmailEmailSource(),
}


class EmailNotConnected(Exception):
    """Raised when a fetch/scan is attempted without an active email integration."""


class EmailService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.integration_repo = EmailIntegrationRepository(db)

    async def connect(
        self,
        user_id: uuid.UUID,
        provider: str,
        access_token: str,
        refresh_token: str | None,
        token_expires_at: datetime | None,
    ) -> EmailIntegration:
        return await self.integration_repo.upsert(
            user_id, access_token, refresh_token, token_expires_at, provider=provider
        )

    async def disconnect(self, user_id: uuid.UUID) -> bool:
        return await self.integration_repo.deactivate(user_id)

    # ── Read-only fetch (refresh the token if needed; never touches the body) ──

    async def _fresh_access_token(self, integration: EmailIntegration) -> str:
        """Return a usable access token, refreshing via the stored refresh token if the current one
        has expired. Unlike the on-demand calendar reads, an email scan can't re-prompt the user, so
        we refresh here (the first token-refresh path in the codebase)."""
        expires = integration.token_expires_at
        if expires is not None and expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires is not None and expires <= datetime.now(UTC) and integration.refresh_token:
            tokens = await gmail_oauth.refresh_access_token(integration.refresh_token)
            await self.integration_repo.upsert(
                integration.user_id, tokens.access_token, tokens.refresh_token,
                tokens.expires_at, provider=integration.provider,
            )
            return tokens.access_token
        return integration.access_token

    async def fetch_recent(self, user_id: uuid.UUID, max_results: int = 25) -> list[EmailMessage]:
        """Read recent unread Primary emails (metadata + snippet only). Raises EmailNotConnected if
        the user has no active integration."""
        integration = await self.integration_repo.get_active(user_id)
        if integration is None:
            raise EmailNotConnected()
        provider = _PROVIDERS.get(integration.provider)
        if provider is None:
            raise EmailNotConnected()
        access_token = await self._fresh_access_token(integration)
        return await provider.list_recent_emails(access_token, max_results=max_results)
