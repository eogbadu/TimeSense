from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "timesense",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.health_task",
        "app.workers.notification_tasks",
        "app.workers.insights_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    beat_schedule={
        "send-morning-checkins": {
            "task": "timesense.send_morning_checkins",
            "schedule": crontab(hour=8, minute=0),
        },
        "send-learning-prompts": {
            "task": "timesense.send_learning_prompts",
            "schedule": crontab(hour=10, minute=0),
        },
        "send-evening-checkouts": {
            "task": "timesense.send_evening_checkouts",
            "schedule": crontab(hour=21, minute=0),
        },
        "generate-weekly-insights": {
            "task": "timesense.generate_weekly_insights",
            "schedule": crontab(day_of_week=1, hour=5, minute=0),
        },
    },
)
