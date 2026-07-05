from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from app.core.security import TokenUser

MOCK_USER = TokenUser(uid="uid-now-1", email="now@example.com", role="user", email_verified=True)
OTHER_USER = TokenUser(uid="uid-now-2", email="now-other@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={
            "uid": user.uid,
            "email": user.email,
            "role": user.role,
            "email_verified": user.email_verified,
        },
    )


@pytest.mark.anyio
async def test_now_authenticated(client):
    """Returns 200 with greeting and usable_minutes."""
    with _mock_verify(MOCK_USER):
        r = await client.get("/api/v1/now", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert "greeting" in data
    assert isinstance(data["usable_minutes"], int)
    assert data["usable_minutes"] >= 0


@pytest.mark.anyio
async def test_now_no_tasks_best_task_null(client):
    """No tasks → best_task is null."""
    with _mock_verify(MOCK_USER):
        r = await client.get("/api/v1/now", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json()["best_task"] is None


@pytest.mark.anyio
async def test_now_picks_highest_priority(client):
    """Returns the highest-priority (lowest number) pending task."""
    today = datetime.now(timezone.utc).date().isoformat()
    with _mock_verify(MOCK_USER):
        await client.post(
            "/api/v1/tasks",
            headers=_auth_headers(),
            json={"title": "Low priority task", "priority": 5,
                  "scheduled_start": f"{today}T09:00:00Z", "source": "manual"},
        )
        await client.post(
            "/api/v1/tasks",
            headers=_auth_headers(),
            json={"title": "High priority task", "priority": 1,
                  "scheduled_start": f"{today}T10:00:00Z", "source": "manual"},
        )
        r = await client.get("/api/v1/now", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json()["best_task"]["title"] == "High priority task"


@pytest.mark.anyio
async def test_now_picks_overdue_task(client):
    """Overdue task (due_at in the past) is included as a candidate."""
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    with _mock_verify(MOCK_USER):
        await client.post(
            "/api/v1/tasks",
            headers=_auth_headers(),
            json={"title": "Overdue task", "priority": 1, "due_at": yesterday, "source": "manual"},
        )
        r = await client.get("/api/v1/now", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json()["best_task"]["title"] == "Overdue task"


@pytest.mark.anyio
async def test_now_done_task_excluded(client):
    """Completed tasks are not returned as best_task."""
    today = datetime.now(timezone.utc).date().isoformat()
    with _mock_verify(MOCK_USER):
        resp = await client.post(
            "/api/v1/tasks",
            headers=_auth_headers(),
            json={"title": "Done task", "priority": 1,
                  "scheduled_start": f"{today}T08:00:00Z", "source": "manual"},
        )
        task_id = resp.json()["id"]
        await client.patch(
            f"/api/v1/tasks/{task_id}",
            headers=_auth_headers(),
            json={"status": "done"},
        )
        r = await client.get("/api/v1/now", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json()["best_task"] is None


@pytest.mark.anyio
async def test_now_unauthenticated(client):
    r = await client.get("/api/v1/now")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_now_surfaces_unscheduled_captured_task(client, db_session):
    """A just-captured task (pending, no scheduled_start, no due_at) must appear as best_task."""
    from app.services.user_service import UserService
    from app.models.task import Task

    user, _ = await UserService(db_session).get_or_create_user(MOCK_USER.uid, MOCK_USER.email)
    db_session.add(Task(user_id=user.id, title="Buy milk", status="pending", priority=3))
    await db_session.flush()

    with _mock_verify(MOCK_USER):
        r = await client.get("/api/v1/now", headers=_auth_headers())
    assert r.status_code == 200
    best = r.json()["best_task"]
    assert best is not None
    assert best["title"] == "Buy milk"


@pytest.mark.anyio
async def test_now_excludes_not_now_task(client, db_session):
    """A 'not now' feedback suppresses the task so a different best task surfaces."""
    from app.services.user_service import UserService
    from app.models.task import Task
    from app.models.recommendation_feedback import RecommendationFeedback

    user, _ = await UserService(db_session).get_or_create_user(MOCK_USER.uid, MOCK_USER.email)
    dismissed = Task(user_id=user.id, title="Dismissed", status="pending", priority=1)
    keep = Task(user_id=user.id, title="Keep", status="pending", priority=2)
    db_session.add_all([dismissed, keep])
    await db_session.flush()
    db_session.add(RecommendationFeedback(user_id=user.id, task_id=dismissed.id, signal="not_now"))
    await db_session.flush()

    with _mock_verify(MOCK_USER):
        r = await client.get("/api/v1/now", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    best = r.json()["best_task"]
    assert best is not None and best["title"] == "Keep"
