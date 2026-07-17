"""Celery task: schedule + deliver pre-appointment reminders (TIME-251).

Runs every couple of minutes. Producer creates a pending InternalReminder for each new upcoming
appointment; consumer delivers the ones whose time has arrived via APNs. All logic lives in
AppointmentReminderService. No-op for delivery unless APNs is configured — same precedent as the
other worker tasks (not exercised by tests in this environment; no Redis/Docker)."""

import asyncio

from app.core.database import AsyncSessionLocal
from app.services.appointment_reminder_service import AppointmentReminderService
from app.workers.celery_app import celery_app


async def _run() -> int:
    async with AsyncSessionLocal() as db:
        return await AppointmentReminderService(db).run()


@celery_app.task(name="timesense.send_appointment_reminders")
def send_appointment_reminders() -> int:
    return asyncio.run(_run())
