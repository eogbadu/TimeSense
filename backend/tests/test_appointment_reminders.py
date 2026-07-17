"""TIME-251 — pre-appointment push notifications.

One reminder per appointment: a departure reminder (10 min before you need to drive) when the appt
has a location and we can compute travel, otherwise a start reminder (10 min before it begins).
Fakes stand in for APNs (FakeSender) and maps (FakeMaps) so we test the scheduling/delivery logic.
"""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 — register all tables on Base.metadata
from app.models.base import Base
from app.models.task import InternalReminder, Task
from app.repositories.device_token_repository import DeviceTokenRepository
from app.repositories.internal_reminder_repository import InternalReminderRepository
from app.repositories.user_place_repository import UserPlaceRepository
from app.services.appointment_reminder_service import AppointmentReminderService
from app.services.recommendation.types import Coordinates
from app.services.user_service import UserService

TEST_DB = "sqlite+aiosqlite:///:memory:"
NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DB, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── Fakes ──────────────────────────────────────────────────────────────────────

class FakeSender:
    available = True

    def __init__(self):
        self.sent: list[tuple] = []

    async def send(self, token, title, body, collapse_id=None, data=None):
        self.sent.append((token, title, body, data))
        return True


class FakeMaps:
    def __init__(self, available=True, travel_minutes: float | None = 20.0,
                 geocode=Coordinates(latitude=10.0, longitude=20.0)):
        self._available = available
        self._travel = travel_minutes
        self._geo = geocode

    @property
    def available(self):
        return self._available

    async def geocode_address(self, address):
        return self._geo

    async def get_travel_estimate(self, request):
        if self._travel is None:
            return None
        return SimpleNamespace(duration_minutes=self._travel)


# ── Helpers ─────────────────────────────────────────────────────────────────────

async def _seed_user(db, uid="uid-appt", email="appt@example.com", with_token=True):
    user, _ = await UserService(db).get_or_create_user(uid, email)
    if with_token:
        await DeviceTokenRepository(db).upsert(user.id, f"tok-{uid}")
    await db.commit()
    return user


async def _add_task(db, user, **kw):
    task = Task(user_id=user.id, title=kw.pop("title", "Meeting"), status=kw.pop("status", "pending"),
                priority=kw.pop("priority", 3), **kw)
    db.add(task)
    await db.commit()
    return task


async def _reminders(db):
    rows = await db.execute(select(InternalReminder))
    return list(rows.scalars().all())


# ── Tests ────────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_start_reminder_for_non_located_appt(db_session):
    user = await _seed_user(db_session)
    await _add_task(db_session, user, title="Standup", scheduled_start=NOW + timedelta(minutes=8))
    sender = FakeSender()

    sent = await AppointmentReminderService(db_session, sender=sender, maps=FakeMaps()).run(now=NOW)

    assert sent == 1
    assert sender.sent and "Standup in 10 minutes" == sender.sent[0][1]
    rows = await _reminders(db_session)
    assert len(rows) == 1 and rows[0].type == "appointment_start" and rows[0].status == "delivered"


@pytest.mark.anyio
async def test_departure_reminder_for_located_appt(db_session):
    user = await _seed_user(db_session)
    await UserPlaceRepository(db_session).replace_all(
        user.id, [{"name": "Home", "latitude": 1.0, "longitude": 2.0}]
    )
    task = await _add_task(db_session, user, title="Dentist", location_name="123 Main St",
                           scheduled_start=NOW + timedelta(minutes=40))
    sender = FakeSender()
    maps = FakeMaps(travel_minutes=20.0)

    # departure = start - 20 - 10 = NOW+10 → not due yet
    sent = await AppointmentReminderService(db_session, sender=sender, maps=maps).run(now=NOW)
    assert sent == 0
    rows = await _reminders(db_session)
    assert len(rows) == 1 and rows[0].type == "appointment_departure" and rows[0].status == "pending"
    # geocoded coords persisted onto the task
    await db_session.refresh(task)
    assert task.location_lat == 10.0 and task.location_lng == 20.0

    # 11 min later the departure reminder is due
    sent2 = await AppointmentReminderService(db_session, sender=sender, maps=maps).run(
        now=NOW + timedelta(minutes=11)
    )
    assert sent2 == 1
    assert "Time to leave for Dentist" == sender.sent[0][1]
    assert "about 20 min" in sender.sent[0][2]


@pytest.mark.anyio
async def test_located_appt_without_origin_falls_back_to_start(db_session):
    user = await _seed_user(db_session)  # no saved Home, no location state
    await _add_task(db_session, user, title="Interview", location_name="Somewhere",
                    scheduled_start=NOW + timedelta(minutes=40))

    await AppointmentReminderService(db_session, sender=FakeSender(), maps=FakeMaps()).run(now=NOW)

    rows = await _reminders(db_session)
    assert len(rows) == 1 and rows[0].type == "appointment_start"


@pytest.mark.anyio
async def test_idempotent_no_double_schedule_or_send(db_session):
    user = await _seed_user(db_session)
    await _add_task(db_session, user, title="Standup", scheduled_start=NOW + timedelta(minutes=8))
    sender = FakeSender()
    svc = AppointmentReminderService(db_session, sender=sender, maps=FakeMaps())

    first = await svc.run(now=NOW)
    second = await AppointmentReminderService(db_session, sender=sender, maps=FakeMaps()).run(now=NOW)

    assert first == 1 and second == 0
    assert len(sender.sent) == 1
    assert len(await _reminders(db_session)) == 1


@pytest.mark.anyio
async def test_stale_reminder_is_expired_not_sent(db_session):
    user = await _seed_user(db_session)
    task = await _add_task(db_session, user, title="Late", scheduled_start=NOW + timedelta(minutes=8))
    # a pending reminder whose trigger is well past the grace window
    await InternalReminderRepository(db_session).create_pending(
        user.id, task.id, "appointment_start", NOW - timedelta(hours=1)
    )
    await db_session.commit()
    sender = FakeSender()

    sent = await AppointmentReminderService(db_session, sender=sender, maps=FakeMaps()).run(now=NOW)

    assert sent == 0 and sender.sent == []
    rows = await _reminders(db_session)
    assert len(rows) == 1 and rows[0].status == "expired"


@pytest.mark.anyio
async def test_no_device_tokens_no_reminders(db_session):
    user = await _seed_user(db_session, with_token=False)
    await _add_task(db_session, user, title="Standup", scheduled_start=NOW + timedelta(minutes=8))
    sender = FakeSender()

    sent = await AppointmentReminderService(db_session, sender=sender, maps=FakeMaps()).run(now=NOW)

    assert sent == 0 and sender.sent == []
    assert await _reminders(db_session) == []
