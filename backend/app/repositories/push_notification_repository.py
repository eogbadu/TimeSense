from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.push_notification import PushNotification


class PushNotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def latest_for_user(self, user_id: uuid.UUID) -> PushNotification | None:
        rows = await self.db.execute(
            select(PushNotification)
            .where(PushNotification.user_id == user_id)
            .order_by(PushNotification.sent_at.desc())
            .limit(1)
        )
        return rows.scalar_one_or_none()

    async def record(self, user_id: uuid.UUID, action_type: str, title: str, body: str,
                     sent_at: datetime, delivered_count: int) -> PushNotification:
        row = PushNotification(user_id=user_id, action_type=action_type, title=title[:128],
                               body=body, sent_at=sent_at, delivered_count=delivered_count)
        self.db.add(row)
        await self.db.flush()
        return row
