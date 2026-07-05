from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_event import AnalyticsEvent


class AnalyticsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, event_name: str, user_id: uuid.UUID | None, properties: str
    ) -> AnalyticsEvent:
        event = AnalyticsEvent(event_name=event_name, user_id=user_id, properties=properties)
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def counts_by_event(self) -> dict[str, int]:
        result = await self.db.execute(
            select(AnalyticsEvent.event_name, func.count())
            .group_by(AnalyticsEvent.event_name)
            .order_by(func.count().desc())
        )
        return {name: count for name, count in result.all()}
