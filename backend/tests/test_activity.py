"""TIME-158 — HealthKit daily activity (steps / energy / exercise).
TIME-252 — behavioral-data ingest (workouts + hourly steps), health_data-consent gated."""

from unittest.mock import patch

import pytest
from sqlalchemy import func, select

from app.core.security import TokenUser
from app.models.hourly_activity import HourlyActivity
from app.models.workout_session import WorkoutSession

USER = TokenUser(uid="act-1", email="act@example.com", role="user", email_verified=True)

_HDRS = {"Authorization": "Bearer t"}


def _verify():
    return patch("app.core.security.firebase_auth.verify_id_token",
                 return_value={"uid": USER.uid, "email": USER.email, "role": "user",
                               "email_verified": True})


async def _grant_health(client):
    return await client.post("/api/v1/consent/", headers=_HDRS,
                             json={"consent_type": "health_data", "granted": True})


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


_W = {
    "external_id": "w1", "workout_type": "running",
    "started_at": "2026-08-01T07:00:00Z", "ended_at": "2026-08-01T07:30:00Z",
    "duration_minutes": 30, "distance_meters": 5000,
}


@pytest.mark.anyio
async def test_workouts_require_health_consent(client, db_session):
    with _verify():
        r = await client.post("/api/v1/activity/workouts", headers=_HDRS, json={"workouts": [_W]})
    assert r.status_code == 403


@pytest.mark.anyio
async def test_workouts_upsert_dedup_and_normalize_type(client, db_session):
    with _verify():
        await _grant_health(client)
        r1 = await client.post("/api/v1/activity/workouts", headers=_HDRS, json={"workouts": [_W]})
        assert r1.status_code == 200 and r1.json()["accepted"] == 1
        # same external_id re-synced → deduped (still one row), and an unknown type → "other"
        await client.post("/api/v1/activity/workouts", headers=_HDRS,
                          json={"workouts": [_W, {**_W, "external_id": "w2", "workout_type": "yoga"}]})
    rows = (await db_session.execute(select(WorkoutSession).order_by(WorkoutSession.external_id))).scalars().all()
    assert len(rows) == 2
    assert {r.external_id: r.workout_type for r in rows} == {"w1": "running", "w2": "other"}


@pytest.mark.anyio
async def test_hourly_ingest_gated_and_upserts(client, db_session):
    hours = {"hours": [{"hour_start": "2026-08-01T09:00:00Z", "steps": 40},
                       {"hour_start": "2026-08-01T10:00:00Z", "steps": 800}]}
    with _verify():
        blocked = await client.post("/api/v1/activity/hourly", headers=_HDRS, json=hours)
        assert blocked.status_code == 403
        await _grant_health(client)
        ok = await client.post("/api/v1/activity/hourly", headers=_HDRS, json=hours)
        assert ok.status_code == 200 and ok.json()["accepted"] == 2
        # re-post one hour with a new value → upsert, not duplicate
        await client.post("/api/v1/activity/hourly", headers=_HDRS,
                          json={"hours": [{"hour_start": "2026-08-01T09:00:00Z", "steps": 55}]})
    count = (await db_session.execute(select(func.count()).select_from(HourlyActivity))).scalar_one()
    assert count == 2


@pytest.mark.anyio
async def test_now_context_includes_steps(client, db_session):
    with _verify():
        await client.post("/api/v1/activity", headers={"Authorization": "Bearer t"},
                          json={"steps": 6842, "active_energy_kcal": 420})
        now = await client.get("/api/v1/now", headers={"Authorization": "Bearer t"})
    ctx = now.json()["context"]
    assert ctx["steps"] == 6842
    assert ctx["steps_goal"] == 10000
