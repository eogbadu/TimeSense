"""Decide whether to proactively push, and send it.

Rules (from the spec):
  * Only push a recommendation that is `eligible_for_push` (score >= 75 and confidence >= 0.75).
  * Never let the LLM choose — we push the deterministic engine's pick; the LLM only phrases it.
  * Cooldown: don't push within 45 minutes of the last push, and never repeat the same action type
    back-to-back. A high-urgency recommendation of a *different* type may override the cooldown.
  * Never push a fallback ("nothing to do") recommendation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.gateway import LLMGateway
from app.repositories.device_token_repository import DeviceTokenRepository
from app.repositories.push_notification_repository import PushNotificationRepository
from app.services.push.sender import PushSender
from app.services.recommendation.candidate_gather import gather_candidate_tasks
from app.services.recommendation.context_builder import build_user_context
from app.services.recommendation.engine import run_engine
from app.services.recommendation.maps.factory import get_maps_provider
from app.services.recommendation.maps.maps_skill_service import MapsSkillService
from app.services.recommendation.types import Recommendation

COOLDOWN = timedelta(minutes=45)


class ProactivePushService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _in_cooldown(self, last, rec: Recommendation, now: datetime) -> bool:
        if last is None:
            return False
        sent = last.sent_at if last.sent_at.tzinfo else last.sent_at.replace(tzinfo=timezone.utc)
        if now - sent >= COOLDOWN:
            return False
        # Within cooldown. Same type → always suppress. Different type → allow only if urgent.
        if last.action_type == rec.action_type:
            return True
        return rec.urgency != "high"

    async def push_for_user(
        self, user, sender: PushSender, gateway: LLMGateway | None = None,
        now: datetime | None = None,
    ) -> Recommendation | None:
        """Returns the pushed recommendation if a push was sent, else None."""
        now = now or datetime.now(timezone.utc)

        tokens = await DeviceTokenRepository(self.db).list_tokens(user.id)
        if not tokens:
            return None

        candidates, usable, _ = await gather_candidate_tasks(self.db, user, now)
        ctx, _ = await build_user_context(self.db, user, candidates, now, usable)
        maps = MapsSkillService(get_maps_provider())
        rec = await run_engine(ctx, maps=maps, now=now, gateway=gateway)

        if rec.domain == "fallback" or not rec.eligible_for_push:
            return None

        push_repo = PushNotificationRepository(self.db)
        last = await push_repo.latest_for_user(user.id)
        if self._in_cooldown(last, rec, now):
            return None

        delivered = 0
        for token in tokens:
            if await sender.send(token, rec.title, rec.message, collapse_id=rec.action_type):
                delivered += 1

        await push_repo.record(
            user_id=user.id, action_type=rec.action_type, title=rec.title,
            body=rec.message, sent_at=now, delivered_count=delivered,
        )
        await self.db.commit()
        return rec
