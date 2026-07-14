"""
Email integration service (Gmail first).

RULE (same as Slack/calendar-writes): detected action items NEVER become Tasks automatically.
scan() only creates pending EmailActionItem rows; confirm() is the single approval-gated path that
creates a Task.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations import gmail_oauth
from app.integrations.email_source_base import EmailMessage, EmailSourceProvider
from app.integrations.gmail_source import GmailEmailSource
from app.llm.gateway import LLMGateway
from app.models.email_integration import EmailActionItem, EmailIntegration
from app.repositories.consent_repository import ConsentRepository
from app.repositories.email_repository import (
    EmailActionItemRepository,
    EmailIntegrationRepository,
)
from app.repositories.task_repository import TaskRepository
from app.services.action_item_detection import ActionItemDetectionService

# Read-only mail sources, keyed by provider (mirrors SlackService._PROVIDERS).
_PROVIDERS: dict[str, EmailSourceProvider] = {
    "gmail": GmailEmailSource(),
}


class EmailNotConnected(Exception):
    """Raised when a fetch/scan is attempted without an active email integration."""


class EmailConsentRequired(Exception):
    """Raised when a scan is attempted without email_content consent."""


class EmailService:
    def __init__(self, db: AsyncSession, gateway: LLMGateway | None = None) -> None:
        self.db = db
        self.integration_repo = EmailIntegrationRepository(db)
        self.item_repo = EmailActionItemRepository(db)
        self.task_repo = TaskRepository(db)
        self.consent_repo = ConsentRepository(db)
        self.detector = ActionItemDetectionService(gateway) if gateway is not None else None

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

    # ── Scan (detect only — never creates Tasks) ──────────────────────────────

    async def scan(self, user_id: uuid.UUID, max_results: int = 25) -> tuple[int, list[EmailActionItem]]:
        """Read recent emails and detect action items into pending rows. Requires email_content
        consent. Raises EmailConsentRequired / EmailNotConnected."""
        effective = await self.consent_repo.get_effective(user_id)
        if not effective.get("email_content"):
            raise EmailConsentRequired()
        assert self.detector is not None, "EmailService needs an LLM gateway to scan."

        emails = await self.fetch_recent(user_id, max_results=max_results)
        detected: list[EmailActionItem] = []
        for email in emails:
            if await self.item_repo.exists_for_message(user_id, email.message_id):
                continue
            result = await self.detector.detect(email.detection_text)
            if not result.is_action_item:
                continue
            item = await self.item_repo.create(
                user_id=user_id, message_id=email.message_id, thread_id=email.thread_id,
                subject=email.subject, sender=email.sender, source_text=email.snippet,
                detected_title=result.title, detected_priority=result.priority,
                detected_estimated_minutes=result.estimated_minutes,
            )
            detected.append(item)
        return len(emails), detected

    # ── Approval gate ─────────────────────────────────────────────────────────

    async def list_pending(self, user_id: uuid.UUID) -> list[EmailActionItem]:
        return await self.item_repo.list_pending(user_id)

    async def confirm(self, user_id: uuid.UUID, item_id: uuid.UUID) -> EmailActionItem:
        """Create a real Task from a pending item — the only path that turns an email into a Task."""
        item = await self.item_repo.get(item_id, user_id)
        if item is None:
            raise ValueError("Action item not found.")
        if item.status != "pending":
            raise ValueError(f"Action item already {item.status}.")
        task = await self.task_repo.create(
            user_id=user_id,
            title=item.detected_title,
            priority=item.detected_priority,
            estimated_minutes=item.detected_estimated_minutes,
            source="email",
            raw_input=item.source_text,
        )
        item.status = "confirmed"
        item.created_task_id = task.id
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def reject(self, user_id: uuid.UUID, item_id: uuid.UUID) -> bool:
        item = await self.item_repo.get(item_id, user_id)
        if item is None or item.status != "pending":
            return False
        item.status = "rejected"
        await self.db.flush()
        return True
