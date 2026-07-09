"""TIME-158 — HealthKit daily activity (steps / energy / exercise)."""

from unittest.mock import patch

import pytest

from app.core.security import TokenUser

USER = TokenUser(uid="act-1", email="act@example.com", role="user", email_verified=True)


def _verify():
    return patch("app.core.security.firebase_auth.verify_id_token",
                 return_value={"uid": USER.uid, "email": USER.email, "role": "user",
                               "email_verified": True})


@pytest.mark.anyio
async def test_sync_and_read_activity(client, db_session):
    with _verify():
        r = await client.post("/api/v1/activity", headers={"Authorization": "Bearer t"},
                              json={"steps": 6842, "active_energy_kcal": 420, "exercise_minutes": 45})
        assert r.status_code == 200 and r.json()["steps"] == 6842
        got = await client.get("/api/v1/activity/today", headers={"Authorization": "Bearer t"})
    body = got.json()
    assert body["steps"] == 6842 and body["exercise_minutes"] == 45


@pytest.mark.anyio
async def test_sync_upserts_same_day(client, db_session):
    with _verify():
        await client.post("/api/v1/activity", headers={"Authorization": "Bearer t"}, json={"steps": 100})
        await client.post("/api/v1/activity", headers={"Authorization": "Bearer t"}, json={"steps": 5000})
        got = await client.get("/api/v1/activity/today", headers={"Authorization": "Bearer t"})
    assert got.json()["steps"] == 5000  # replaced, not duplicated


@pytest.mark.anyio
async def test_now_context_includes_steps(client, db_session):
    with _verify():
        await client.post("/api/v1/activity", headers={"Authorization": "Bearer t"},
                          json={"steps": 6842, "active_energy_kcal": 420})
        now = await client.get("/api/v1/now", headers={"Authorization": "Bearer t"})
    ctx = now.json()["context"]
    assert ctx["steps"] == 6842
    assert ctx["steps_goal"] == 10000
