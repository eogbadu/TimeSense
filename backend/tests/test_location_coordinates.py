"""TIME-291 — the location signal, repaired end to end (backend half).

The signal had stopped influencing recommendations. Six things were wrong; the two the backend owns:

  * coordinates were never stored, and were only back-filled when the reported place name happened
    to match a saved UserPlace EXACTLY — so a user standing anywhere unsaved produced
    LOCATION_DATA_MISSING and errands could never be travel-checked;
  * the stored fix went stale after six hours with nothing to bring it back.

Storing a position is a real privacy change, so these also pin the limits: consent is required, and
only the CURRENT position is kept — the row is overwritten, never appended to.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.security import TokenUser

USER = TokenUser(uid="uid-loc-1", email="loc@example.com", role="user", email_verified=True)


def _auth():
    return {"Authorization": "Bearer test-token"}


def _verify(user: TokenUser = USER):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role,
                      "email_verified": user.email_verified},
    )


async def _grant_location(client):
    r = await client.post("/api/v1/consent/", headers=_auth(),
                          json={"consent_type": "location_tracking", "granted": True})
    assert r.status_code in (200, 201), r.text


@pytest.mark.anyio
async def test_coordinates_are_stored_with_consent(client):
    with _verify():
        await _grant_location(client)
        r = await client.post("/api/v1/location/place", headers=_auth(),
                              json={"place_name": "Home", "is_home": True,
                                    "latitude": 51.5072, "longitude": -0.1276})
    assert r.status_code == 200, r.text
    assert r.json()["has_coordinates"] is True


@pytest.mark.anyio
async def test_coordinates_are_dropped_without_consent(client):
    """Without location consent the name is stored exactly as before and the position is discarded.
    Behaviour degrades to the pre-TIME-291 state rather than failing."""
    with _verify():
        r = await client.post("/api/v1/location/place", headers=_auth(),
                              json={"place_name": "Home", "is_home": True,
                                    "latitude": 51.5072, "longitude": -0.1276})
    assert r.status_code == 200, r.text
    assert r.json()["place_name"] == "Home"
    assert r.json()["has_coordinates"] is False


@pytest.mark.anyio
async def test_only_the_current_position_is_kept_never_a_history(client, db_session):
    """The privacy limit that makes this acceptable: one row, overwritten. A trail of movement is
    still never persisted."""
    from sqlalchemy import func, select

    from app.models.user_location_state import UserLocationState

    with _verify():
        await _grant_location(client)
        for lat, lng in [(51.50, -0.12), (48.85, 2.35), (40.71, -74.00)]:
            await client.post("/api/v1/location/place", headers=_auth(),
                              json={"place_name": None, "is_home": False,
                                    "latitude": lat, "longitude": lng})

    count = (await db_session.execute(
        select(func.count()).select_from(UserLocationState)
    )).scalar_one()
    assert count == 1, "a location history accumulated"

    row = (await db_session.execute(select(UserLocationState))).scalar_one()
    assert (round(row.latitude, 2), round(row.longitude, 2)) == (40.71, -74.00)


@pytest.mark.anyio
async def test_a_name_only_report_does_not_erase_a_known_position(client):
    """A geofence crossing may carry no fresh fix. Treating that as "no location" would throw away
    a perfectly good position and put errands back to LOCATION_DATA_MISSING."""
    with _verify():
        await _grant_location(client)
        await client.post("/api/v1/location/place", headers=_auth(),
                          json={"place_name": "Home", "is_home": True,
                                "latitude": 51.5072, "longitude": -0.1276})
        r = await client.post("/api/v1/location/place", headers=_auth(),
                              json={"place_name": "Home", "is_home": True})
    assert r.json()["has_coordinates"] is True


@pytest.mark.anyio
async def test_the_snapshot_exposes_coordinates_so_errands_can_be_travel_checked(client, db_session):
    """The actual payoff: the engine's location snapshot now carries an origin."""
    from app.repositories.user_repository import UserRepository
    from app.services.recommendation.location_service import get_user_location_snapshot

    with _verify():
        await _grant_location(client)
        await client.post("/api/v1/location/place", headers=_auth(),
                          json={"place_name": None, "is_home": False,
                                "latitude": 51.5072, "longitude": -0.1276})

    user = await UserRepository(db_session).get_by_email(USER.email)
    snapshot = await get_user_location_snapshot(db_session, user.id)
    assert snapshot.coordinates is not None
    assert round(snapshot.coordinates.latitude, 3) == 51.507


@pytest.mark.anyio
async def test_the_client_is_told_to_refresh_before_the_signal_goes_stale(db_session):
    """Previously the fix simply expired at six hours and the signal vanished with nothing to bring
    it back."""
    from app.repositories.user_location_repository import (
        REFRESH_BEFORE,
        STALE_AFTER,
        UserLocationRepository,
    )
    from app.services.user_service import UserService

    user, _ = await UserService(db_session).get_or_create_user("uid-loc-2", "loc2@example.com")
    repo = UserLocationRepository(db_session)
    row = await repo.upsert(user.id, "Home", True, latitude=51.5, longitude=-0.1)

    now = datetime.now(timezone.utc)
    assert await repo.is_stale_soon(user.id, now=now) is False

    row.updated_at = now - (STALE_AFTER - REFRESH_BEFORE) - timedelta(minutes=1)
    await db_session.flush()
    assert await repo.is_stale_soon(user.id, now=now) is True


@pytest.mark.anyio
async def test_out_of_range_coordinates_are_rejected(client):
    with _verify():
        await _grant_location(client)
        for lat, lng in [(91, 0), (-91, 0), (0, 181), (0, -181)]:
            r = await client.post("/api/v1/location/place", headers=_auth(),
                                  json={"place_name": None, "is_home": False,
                                        "latitude": lat, "longitude": lng})
            assert r.status_code == 422, f"({lat}, {lng}) should have been rejected"
