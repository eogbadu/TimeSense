from datetime import UTC, datetime

from app.workers.celery_app import celery_app


@celery_app.task(name="timesense.health_check")
def health_check() -> dict:
    return {
        "status": "ok",
        "worker": "timesense",
        "timestamp": datetime.now(UTC).isoformat(),
    }
