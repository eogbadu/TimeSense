"""Nightly rebuild of every active user's adaptation profile.

Follows the same shape as the weekly-insights job: iterate active users, drive a service, commit
once. The point of doing it here rather than on demand is that the engine reads the result on EVERY
recommendation — recomputing 42 days of history per request is exactly why the old live-computed
"learned preferences" never made it into scoring (TIME-292).
"""
import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.repositories.user_repository import UserRepository
from app.services.user_adaptation_service import UserAdaptationService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _rebuild_all() -> int:
    built = 0
    async with AsyncSessionLocal() as db:
        user_ids = await UserRepository(db).list_active_ids()
        svc = UserAdaptationService(db)
        for user_id in user_ids:
            try:
                await svc.rebuild(user_id)
                built += 1
            except Exception:
                # One user's bad data must not stop the sweep — the profile is derived, so a miss
                # just means that user keeps yesterday's (or stays neutral).
                logger.exception("adaptation profile rebuild failed for %s", user_id)
        await db.commit()
    return built


@celery_app.task(name="timesense.rebuild_adaptation_profiles")
def rebuild_adaptation_profiles() -> int:
    return asyncio.run(_rebuild_all())
