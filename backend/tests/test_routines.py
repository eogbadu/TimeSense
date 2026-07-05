from unittest.mock import patch

import pytest

from app.core.security import TokenUser
from app.models.routine import ROUTINE_TYPES

MOCK_USER = TokenUser(uid="uid-routine-1", email="routine@example.com", role="user", email_verified=True)
OTHER_USER = TokenUser(uid="uid-routine-2", email="routine-other@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


@pytest.mark.anyio
async def test_list_routines_seeds_defaults(client):
    with _mock_verify(MOCK_USER):
        r = await client.get("/api/v1/routines", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert len(data) == len(ROUTINE_TYPES)
    assert {row["routine_type"] for row in data} == set(ROUTINE_TYPES)
    assert all(row["is_customized"] is False for row in data)


@pytest.mark.anyio
async def test_list_routines_idempotent_seeding(client):
    with _mock_verify(MOCK_USER):
        await client.get("/api/v1/routines", headers=_auth_headers())
        r = await client.get("/api/v1/routines", headers=_auth_headers())
    assert r.status_code == 200
    assert len(r.json()) == len(ROUTINE_TYPES)


@pytest.mark.anyio
async def test_sleep_default_wraps_past_midnight(client):
    with _mock_verify(MOCK_USER):
        r = await client.get("/api/v1/routines", headers=_auth_headers())
    sleep = next(row for row in r.json() if row["routine_type"] == "sleep")
    assert sleep["start_minute"] == 23 * 60
    assert sleep["end_minute"] == 7 * 60


@pytest.mark.anyio
async def test_update_routine(client):
    with _mock_verify(MOCK_USER):
        r = await client.patch(
            "/api/v1/routines/lunch",
            headers=_auth_headers(),
            json={"start_minute": 13 * 60, "end_minute": 13 * 60 + 45},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["start_minute"] == 13 * 60
    assert data["end_minute"] == 13 * 60 + 45
    assert data["is_customized"] is True


@pytest.mark.anyio
async def test_update_persists(client):
    with _mock_verify(MOCK_USER):
        await client.patch(
            "/api/v1/routines/lunch",
            headers=_auth_headers(),
            json={"start_minute": 13 * 60, "end_minute": 13 * 60 + 45},
        )
        r = await client.get("/api/v1/routines", headers=_auth_headers())
    lunch = next(row for row in r.json() if row["routine_type"] == "lunch")
    assert lunch["start_minute"] == 13 * 60
    assert lunch["is_customized"] is True


@pytest.mark.anyio
async def test_update_unknown_routine_type_404(client):
    with _mock_verify(MOCK_USER):
        r = await client.patch(
            "/api/v1/routines/snacking",
            headers=_auth_headers(),
            json={"start_minute": 60, "end_minute": 90},
        )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_update_out_of_range_minute_422(client):
    with _mock_verify(MOCK_USER):
        r = await client.patch(
            "/api/v1/routines/lunch",
            headers=_auth_headers(),
            json={"start_minute": 1500, "end_minute": 90},
        )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_routines_are_per_user(client):
    with _mock_verify(MOCK_USER):
        await client.patch(
            "/api/v1/routines/lunch",
            headers=_auth_headers(),
            json={"start_minute": 13 * 60, "end_minute": 13 * 60 + 45},
        )
    with _mock_verify(OTHER_USER):
        r = await client.get("/api/v1/routines", headers=_auth_headers())
    lunch = next(row for row in r.json() if row["routine_type"] == "lunch")
    assert lunch["is_customized"] is False
    assert lunch["start_minute"] == 12 * 60


@pytest.mark.anyio
async def test_routines_unauthenticated(client):
    r = await client.get("/api/v1/routines")
    assert r.status_code == 401
