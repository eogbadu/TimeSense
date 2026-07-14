"""
Email integration service (Gmail first).

RULE (same as Slack/calendar-writes): detected action items NEVER become Tasks automatically. This
first slice only handles the read-only OAuth connection; scanning + the approval-gated confirm() land
in TIME-215/216.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_integration import EmailIntegration
from app.repositories.email_repository import EmailIntegrationRepository


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
