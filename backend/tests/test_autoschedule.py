"""Auto-schedule + unschedule (TIME-085)."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest


def _verify(uid, email):
    return patch("app.core.security.firebase_auth.verify_id_token",
                 return_value={"uid": uid, "email": email, "role": "user", "email_verified": True})


@pytest.mark.anyio
async def test_unschedule_clears_time(client, db_session):
    from app.services.user_service import UserService
    from app.models.task import Task

    user, _ = await UserService(db_session).get_or_create_user("uns-1", "uns@example.com")
    now = datetime.now(timezone.utc)
    t = Task(user_id=user.id, title="Placed errand", status="pending", priority=3,
             scheduled_start=now, scheduled_end=now + timedelta(minutes=30), auto_scheduled=True)
    db_session.add(t)
    await db_session.flush()

    with _verify("uns-1", "uns@example.com"):
        r = await client.post(f"/api/v1/tasks/{t.id}/unschedule", headers={"Authorization": "Bearer t"}, json={})
    assert r.status_code == 200
    body = r.json()
    assert body["scheduled_start"] is None
    assert body["auto_scheduled"] is False


@pytest.mark.anyio
async def test_capture_response_has_auto_scheduled_field(client):
    """Captured tasks expose auto_scheduled (may be true/false depending on the hour + slots)."""
    with _verify("cap-as-1", "capas@example.com"):
        r = await client.post("/api/v1/capture", headers={"Authorization": "Bearer t"},
                              json={"raw_input": "Buy groceries"})
    assert r.status_code == 201
    assert "auto_scheduled" in r.json()
