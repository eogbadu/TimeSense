"""
Thin Celery wrappers around NotificationService's gated check-in/learning-prompt methods.
All decision logic lives in NotificationService (unit-tested against db_session); these tasks
just iterate active users and drive it on a schedule. Not covered by tests in this environment —
no Redis/Docker available, same precedent as app.workers.health_task.

Scheduling note (TIME-283): these used to run once a day at a fixed UTC hour, which meant a
"morning check-in" arrived at 5pm for a user in Tokyo and at 3am for one in Los Angeles. They now
run HOURLY and each user is only processed during the hour that is their own local check-in time.
Nothing here is region-specific — it works for any IANA zone the device reports, including
half-hour offsets, and follows a user who travels as soon as their profile timezone updates.
"""
import asyncio

from app.core.localtime import local_hour
from app.core.database import AsyncSessionLocal
from app.repositories.user_repository import UserRepository
from app.services.notification_service import NotificationService
from app.workers.celery_app import celery_app

# The user's LOCAL hour at which each check-in is due.
MORNING_CHECKIN_HOUR = 8
LEARNING_PROMPT_HOUR = 10
EVENING_CHECKOUT_HOUR = 21


async def _run_for_users_at_local_hour(method_name: str, target_hour: int) -> int:
    """Drive `method_name` for every active user for whom it is currently `target_hour` locally.

    Runs hourly; each user matches in exactly one run per day. The service methods are already
    idempotent per day (they check notification_events), so an extra run can't double-send.
    """
    sent = 0
    async with AsyncSessionLocal() as db:
        rows = await UserRepository(db).list_active_ids_with_timezone()
        svc = NotificationService(db)
        method = getattr(svc, method_name)
        for user_id, user_tz in rows:
            if local_hour(user_tz) != target_hour:
                continue
            if await method(user_id):
                sent += 1
        await db.commit()
    return sent


@celery_app.task(name="timesense.send_morning_checkins")
def send_morning_checkins() -> int:
    return asyncio.run(
        _run_for_users_at_local_hour("maybe_send_morning_checkin", MORNING_CHECKIN_HOUR)
    )


@celery_app.task(name="timesense.send_evening_checkouts")
def send_evening_checkouts() -> int:
    return asyncio.run(
        _run_for_users_at_local_hour("maybe_send_evening_checkout", EVENING_CHECKOUT_HOUR)
    )


@celery_app.task(name="timesense.send_learning_prompts")
def send_learning_prompts() -> int:
    return asyncio.run(
        _run_for_users_at_local_hour("maybe_send_routine_learning_prompt", LEARNING_PROMPT_HOUR)
    )
