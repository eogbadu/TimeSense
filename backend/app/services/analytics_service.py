"""
Analytics event pipeline.

Privacy-respecting: a user-attributed event is only recorded when that user has granted the
'analytics' consent. System-level events (no user_id) are recorded without a consent check.
properties carry non-PII product signals only.
"""
from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_event import AnalyticsEvent
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.consent_repository import ConsentRepository

logger = logging.getLogger(__name__)

ANALYTICS_CONSENT = "analytics"


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AnalyticsRepository(db)
        self.consent_repo = ConsentRepository(db)

    async def track(
        self,
        event_name: str,
        user_id: uuid.UUID | None = None,
        properties: dict | None = None,
    ) -> AnalyticsEvent | None:
        """Record an analytics event. Returns None (skips) if the user hasn't consented to analytics.

        Never raises — analytics must not break the request it rides along with.
        """
        try:
            if user_id is not None:
                effective = await self.consent_repo.get_effective(user_id)
                if not effective.get(ANALYTICS_CONSENT, False):
                    return None
            return await self.repo.create(
                event_name=event_name,
                user_id=user_id,
                properties=json.dumps(properties or {}),
            )
        except Exception as exc:  # noqa: BLE001 — analytics is best-effort
            logger.warning("Analytics track failed for %s: %s", event_name, exc)
            return None
