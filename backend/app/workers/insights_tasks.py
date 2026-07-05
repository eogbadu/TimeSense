"""
Thin Celery wrapper around InsightsService.get_or_generate_latest(). All aggregation/LLM
logic lives in the tested service; this task just iterates active users on a weekly
schedule. Not covered by tests in this environment — no Redis/Docker available, same
precedent as app.workers.health_task/notification_tasks.
"""
import asyncio

from app.core.database import AsyncSessionLocal
from app.llm.gateway import get_llm_gateway
from app.repositories.user_repository import UserRepository
from app.services.insights_service import InsightsService
from app.workers.celery_app import celery_app


async def _generate_for_all_active_users() -> int:
    generated = 0
    async with AsyncSessionLocal() as db:
        user_ids = await UserRepository(db).list_active_ids()
        gateway = get_llm_gateway()
        svc = InsightsService(db, gateway)
        for user_id in user_ids:
            await svc.get_or_generate_latest(user_id)
            generated += 1
        await db.commit()
    return generated


@celery_app.task(name="timesense.generate_weekly_insights")
def generate_weekly_insights() -> int:
    return asyncio.run(_generate_for_all_active_users())
