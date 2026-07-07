"""Location shapes the recommendation (TIME-108)."""
from unittest.mock import patch
import pytest

from app.core.security import TokenUser

USER = TokenUser(uid="loc-1", email="loc@example.com", role="user", email_verified=True)


def _verify(u=USER):
    return patch("app.core.security.firebase_auth.verify_id_token",
                 return_value={"uid": u.uid, "email": u.email, "role": u.role, "email_verified": True})


@pytest.mark.anyio
async def test_place_update_and_signal(client, db_session):
    from app.services.user_service import UserService
    from app.models.task import Task
    from datetime import datetime, timezone

    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    db_session.add(Task(user_id=user.id, title="Revise paper", status="pending", priority=1,
                        estimated_minutes=45, due_at=datetime.now(timezone.utc)))
    await db_session.flush()

    with _verify():
        # report being at Home
        p = await client.post("/api/v1/location/place", headers={"Authorization": "Bearer t"},
                              json={"place_name": "Home", "is_home": True})
        assert p.status_code == 200 and p.json()["place_name"] == "Home"

        r = await client.get("/api/v1/now", headers={"Authorization": "Bearer t"})
        best = r.json()["best_task"]
        w = await client.get(f"/api/v1/now/why?task_id={best['id']}", headers={"Authorization": "Bearer t"})
    loc = next(s for s in w.json()["signals"] if s["name"] == "Location")
    assert loc["available"] is True and "Home" in loc["detail"]


@pytest.mark.anyio
async def test_location_rerank_promotes_errand_when_out(client, db_session):
    from app.services.user_service import UserService
    from app.models.task import Task

    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    # equal priority: a focus task and an errand
    db_session.add_all([
        Task(user_id=user.id, title="Write the report", status="pending", priority=3),
        Task(user_id=user.id, title="Buy groceries at the store", status="pending", priority=3),
    ])
    await db_session.flush()

    with _verify():
        # out and about
        await client.post("/api/v1/location/place", headers={"Authorization": "Bearer t"},
                          json={"place_name": None, "is_home": False})
        out = await client.get("/api/v1/now", headers={"Authorization": "Bearer t"})
        # at home
        await client.post("/api/v1/location/place", headers={"Authorization": "Bearer t"},
                          json={"place_name": "Home", "is_home": True})
        home = await client.get("/api/v1/now", headers={"Authorization": "Bearer t"})
    # when out, the errand should outrank the focus task; at home it shouldn't lead
    assert "groceries" in out.json()["best_task"]["title"].lower()
    assert "groceries" not in home.json()["best_task"]["title"].lower()
