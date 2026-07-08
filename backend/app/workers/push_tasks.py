"""Celery task: scan users with a registered device and send a proactive push when the engine has a
push-eligible recommendation (outside cooldown). All decision logic lives in ProactivePushService.
No-op unless APNs is configured. Not covered by tests in this environment (no Redis/Docker) — same
precedent as the other worker tasks."""

import asyncio

from app.core.database import AsyncSessionLocal
from app.llm.gateway import get_llm_gateway
from app.repositories.device_token_repository import DeviceTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.push.factory import get_push_sender
from app.services.push.push_service import ProactivePushService
from app.workers.celery_app import celery_app


async def _scan_and_push() -> int:
    sender = get_push_sender()
    if not sender.available:
        return 0  # APNs not configured — nothing to send
    gateway = get_llm_gateway()
    pushed = 0
    async with AsyncSessionLocal() as db:
        user_ids = await DeviceTokenRepository(db).distinct_user_ids()
        for uid in user_ids:
            user = await UserRepository(db).get_by_id(uid)
            if user is None:
                continue
            svc = ProactivePushService(db)
            # Prefer a genuinely push-worthy recommendation; if there isn't one, offer to block time
            # for a high-priority/overdue unscheduled task. Both honor the shared cooldown.
            if await svc.push_for_user(user, sender, gateway=gateway) is not None:
                pushed += 1
            elif await svc.offer_time_block_for_user(user, sender) is not None:
                pushed += 1
    return pushed


@celery_app.task(name="timesense.scan_and_push")
def scan_and_push() -> int:
    return asyncio.run(_scan_and_push())
