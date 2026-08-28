"""TIME-289 — a self-report overrides the inferred energy, for a bounded window.

Inferred energy reads sleep, activity and the clock — proxies, not the person. One tap should be
able to correct it, and that correction has to actually drive recommendations rather than being
cosmetic. It also has to expire: a report from this morning must not still be steering the evening.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.security import TokenUser

MOCK_USER = TokenUser(uid="uid-energy-ci", email="ci@example.com", role="user", email_verified=True)


def _auth():
    return {"Authorization": "Bearer test-token"}


def _verify(user: TokenUser = MOCK_USER):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role,
                      "email_verified": user.email_verified},
    )


@pytest.mark.anyio
async def test_checkin_changes_the_reported_energy(client):
    with _verify():
        before = await client.get("/api/v1/energy", headers=_auth())
        assert before.status_code == 200
        assert before.json()["source"] != "checkin"

        posted = await client.post("/api/v1/energy/checkin", headers=_auth(),
                                   json={"reported": "low"})
        assert posted.status_code == 200, posted.text
        assert posted.json()["level"] == "low"
        assert posted.json()["source"] == "checkin"

        after = await client.get("/api/v1/energy", headers=_auth())
    assert after.json()["level"] == "low"
    assert after.json()["source"] == "checkin"
    assert after.json()["valid_for_minutes"] > 0


@pytest.mark.anyio
async def test_the_why_sheet_attributes_the_value_to_the_user(client):
    """If the user told us, the explanation must say so rather than inventing a health reason."""
    with _verify():
        await client.post("/api/v1/energy/checkin", headers=_auth(), json={"reported": "high"})
        r = await client.get("/api/v1/energy", headers=_auth())
    assert "told us" in r.json()["reason"].lower()


@pytest.mark.anyio
async def test_an_invalid_level_is_rejected(client):
    with _verify():
        for bad in ["exhausted", "MEDIUM ", "", "5"]:
            r = await client.post("/api/v1/energy/checkin", headers=_auth(),
                                  json={"reported": bad})
            assert r.status_code == 422, f"{bad!r} should have been rejected"


@pytest.mark.anyio
async def test_a_checkin_expires_and_stops_steering_the_day(db_session):
    """The bounded window is the point — a report from this morning must not still be in force
    this evening."""
    from app.repositories.energy_checkin_repository import (
        CHECKIN_VALID_FOR,
        EnergyCheckInRepository,
    )
    from app.services.energy_service import EnergyService
    from app.services.user_service import UserService

    user, _ = await UserService(db_session).get_or_create_user("uid-exp", "exp@example.com")
    repo = EnergyCheckInRepository(db_session)
    now = datetime(2026, 8, 3, 15, 0, tzinfo=timezone.utc)

    await repo.create(user.id, reported="high", reported_at=now - timedelta(minutes=30))
    fresh = await EnergyService(db_session).estimate(user.id, now=now, user_timezone="UTC")
    assert fresh.level == "high" and fresh.source == "checkin"

    later = now + CHECKIN_VALID_FOR + timedelta(minutes=1)
    stale = await EnergyService(db_session).estimate(user.id, now=later, user_timezone="UTC")
    assert stale.source != "checkin", "an expired check-in must stop overriding"


@pytest.mark.anyio
async def test_the_most_recent_checkin_wins(db_session):
    from app.repositories.energy_checkin_repository import EnergyCheckInRepository
    from app.services.energy_service import EnergyService
    from app.services.user_service import UserService

    user, _ = await UserService(db_session).get_or_create_user("uid-latest", "l@example.com")
    repo = EnergyCheckInRepository(db_session)
    now = datetime(2026, 8, 3, 15, 0, tzinfo=timezone.utc)

    await repo.create(user.id, reported="low", reported_at=now - timedelta(hours=2))
    await repo.create(user.id, reported="high", reported_at=now - timedelta(minutes=5))

    estimate = await EnergyService(db_session).estimate(user.id, now=now, user_timezone="UTC")
    assert estimate.level == "high"


@pytest.mark.anyio
async def test_the_inferred_value_is_stored_alongside_the_report(client, db_session):
    """The gap between reported and inferred is the only real feedback the energy model has. It is
    collected now and deliberately not acted on yet — the curve should be tuned on evidence, not
    on the first few data points."""
    from app.repositories.energy_checkin_repository import EnergyCheckInRepository
    from app.repositories.user_repository import UserRepository

    with _verify():
        await client.post("/api/v1/energy/checkin", headers=_auth(), json={"reported": "low"})

    user = await UserRepository(db_session).get_by_email(MOCK_USER.email)
    rows = await EnergyCheckInRepository(db_session).list_recent(user.id)
    assert rows, "the check-in was not persisted"
    assert rows[0].reported == "low"
    assert rows[0].inferred in {"low", "medium", "high"}
    assert 0 <= rows[0].inferred_score <= 100


@pytest.mark.anyio
async def test_a_second_checkin_does_not_record_the_first_as_the_models_reading(client, db_session):
    """Otherwise the calibration data would slowly become a record of the user agreeing with
    themselves."""
    from app.repositories.energy_checkin_repository import EnergyCheckInRepository
    from app.repositories.user_repository import UserRepository

    with _verify():
        await client.post("/api/v1/energy/checkin", headers=_auth(), json={"reported": "low"})
        await client.post("/api/v1/energy/checkin", headers=_auth(), json={"reported": "high"})

    user = await UserRepository(db_session).get_by_email(MOCK_USER.email)
    rows = await EnergyCheckInRepository(db_session).list_recent(user.id)
    assert rows[0].reported == "high"
    assert rows[0].inferred is None, "the previous self-report was recorded as an inference"


@pytest.mark.anyio
async def test_only_active_coach_users_are_asked_about_energy(db_session):
    """A second daily notification just to ask one question is exactly the "another job to manage"
    the product rules forbid — so the ask rides along with the existing morning check-in, and only
    for the mode that opted into coaching."""
    from app.repositories.user_repository import UserRepository
    from app.services.notification_service import NotificationService
    from app.services.user_service import UserService

    asks = {}
    for mode in ("gentle", "balanced", "active_coach"):
        user, _ = await UserService(db_session).get_or_create_user(
            f"uid-mode-{mode}", f"{mode}@example.com"
        )
        await UserRepository(db_session).update_preferences(user.id, notification_mode=mode)
        notif = await NotificationService(db_session).maybe_send_morning_checkin(user.id)
        asks[mode] = None if notif is None else ("Energy" in notif.body)

    assert asks["active_coach"] is True
    # Gentle gets no morning check-in at all; balanced gets one, without the energy ask.
    assert asks["gentle"] in (None, False)
    assert asks["balanced"] is False
