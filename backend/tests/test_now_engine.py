"""TIME-114 — /now is now driven by the deterministic engine."""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.security import TokenUser

USER = TokenUser(uid="now-eng", email="now-eng@example.com", role="user", email_verified=True)


def _verify():
    from unittest.mock import patch
    return patch("app.core.security.firebase_auth.verify_id_token",
                 return_value={"uid": USER.uid, "email": USER.email, "role": "user",
                               "email_verified": True})


@pytest.mark.anyio
async def test_engine_orders_doable_task_over_unconfirmable_errand_at_home(client, db_session):
    from app.services.user_service import UserService
    from app.models.task import Task

    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    db_session.add_all([
        Task(user_id=user.id, title="Go to Walmart", status="pending", priority=1,
             due_at=datetime.now(timezone.utc)),
        Task(user_id=user.id, title="Outline the proposal", status="pending", priority=3,
             estimated_minutes=40),
    ])
    await db_session.flush()

    with _verify():
        await client.post("/api/v1/location/place", headers={"Authorization": "Bearer t"},
                          json={"place_name": "Home", "is_home": True})
        r = await client.get("/api/v1/now", headers={"Authorization": "Bearer t"})
    best = r.json()["best_task"]
    assert best is not None and "walmart" not in best["title"].lower()


@pytest.mark.anyio
async def test_engine_still_prefers_overdue(client, db_session):
    from app.services.user_service import UserService
    from app.models.task import Task

    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    db_session.add_all([
        Task(user_id=user.id, title="Overdue invoice", status="pending", priority=2,
             due_at=datetime.now(timezone.utc) - timedelta(days=1), estimated_minutes=20),
        Task(user_id=user.id, title="Someday idea", status="pending", priority=4),
    ])
    await db_session.flush()

    with _verify():
        r = await client.get("/api/v1/now", headers={"Authorization": "Bearer t"})
    assert r.json()["best_task"]["title"] == "Overdue invoice"


@pytest.mark.anyio
async def test_engine_returns_every_task_in_alternatives(client, db_session):
    """The safety net keeps all candidate tasks available (best + alternatives)."""
    from app.services.user_service import UserService
    from app.models.task import Task

    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    for i in range(3):
        db_session.add(Task(user_id=user.id, title=f"Task {i}", status="pending", priority=3,
                            estimated_minutes=20))
    await db_session.flush()

    with _verify():
        r = await client.get("/api/v1/now", headers={"Authorization": "Bearer t"})
    body = r.json()
    titles = {body["best_task"]["title"]} | {a["title"] for a in body["alternatives"]}
    assert titles == {"Task 0", "Task 1", "Task 2"}
