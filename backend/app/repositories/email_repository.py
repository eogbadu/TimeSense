from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_integration import EmailIntegration


class EmailIntegrationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active(self, user_id: uuid.UUID) -> EmailIntegration | None:
        result = await self.db.execute(
            select(EmailIntegration).where(
                EmailIntegration.user_id == user_id,
                EmailIntegration.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: uuid.UUID,
        access_token: str,
        refresh_token: str | None = None,
        token_expires_at: datetime | None = None,
        provider: str = "gmail",
    ) -> EmailIntegration:
        existing = await self.get_active(user_id)
        if existing:
            existing.provider = provider
            existing.access_token = access_token
            # Only overwrite the refresh token when a new one is supplied (Google omits it on refresh).
            if refresh_token is not None:
                existing.refresh_token = refresh_token
            existing.token_expires_at = token_expires_at
            await self.db.flush()
            return existing
        integration = EmailIntegration(
            user_id=user_id, provider=provider, access_token=access_token,
            refresh_token=refresh_token, token_expires_at=token_expires_at,
        )
        self.db.add(integration)
        await self.db.flush()
        return integration

    async def deactivate(self, user_id: uuid.UUID) -> bool:
        integration = await self.get_active(user_id)
        if integration is None:
            return False
        integration.is_active = False
        await self.db.flush()
        return True
