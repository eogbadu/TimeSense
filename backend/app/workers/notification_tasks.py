"""
Thin Celery wrappers around NotificationService's gated check-in/learning-prompt methods.
All decision logic lives in NotificationService (unit-tested against db_session); these tasks
just iterate active users and drive it on a schedule. Not covered by tests in this environment —
no Redis/Docker available, same precedent as app.workers.health_task.
"""
import asyncio

from app.core.database import AsyncSessionLocal
from app.repositories.user_repository import UserRepository
from app.services.notification_service import NotificationService
from app.workers.celery_app import celery_app


async def _run_for_active_users(method_name: str) -> int:
    sent = 0
    async with AsyncSessionLocal() as db:
        user_ids = await UserRepository(db).list_active_ids()
        svc = NotificationService(db)
        method = getattr(svc, method_name)
        for user_id in user_ids:
            if await method(user_id):
                sent += 1
        await db.commit()
    return sent


@celery_app.task(name="timesense.send_morning_checkins")
def send_morning_checkins() -> int:
    return asyncio.run(_run_for_active_users("maybe_send_morning_checkin"))


@celery_app.task(name="timesense.send_evening_checkouts")
def send_evening_checkouts() -> int:
    return asyncio.run(_run_for_active_users("maybe_send_evening_checkout"))


@celery_app.task(name="timesense.send_learning_prompts")
def send_learning_prompts() -> int:
    return asyncio.run(_run_for_active_users("maybe_send_routine_learning_prompt"))
