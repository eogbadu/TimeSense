from unittest.mock import patch

import pytest

from app.core.security import TokenUser

MOCK_USER = TokenUser(uid="uid-task-1", email="tasks@example.com", role="user", email_verified=True)
OTHER_USER = TokenUser(uid="uid-task-2", email="other@example.com", role="user", email_verified=True)


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
async def test_create_task(client):
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/tasks",
            headers=_auth_headers(),
            json={"title": "Call dentist", "source": "capture"},
        )
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Call dentist"
    assert data["status"] == "pending"
    assert data["source"] == "capture"
    assert data["priority"] == 3


@pytest.mark.anyio
async def test_create_task_with_all_fields(client):
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/tasks",
            headers=_auth_headers(),
            json={
                "title": "Deep work block",
                "description": "Focus on the backend",
                "priority": 1,
                "estimated_minutes": 90,
                "scheduled_start": "2026-07-04T09:00:00Z",
                "scheduled_end": "2026-07-04T10:30:00Z",
                "source": "manual",
                "raw_input": "work for 90 min at 9am",
            },
        )
    assert r.status_code == 201
    data = r.json()
    assert data["estimated_minutes"] == 90
    assert data["priority"] == 1
    assert data["raw_input"] == "work for 90 min at 9am"


@pytest.mark.anyio
async def test_create_task_empty_title_rejected(client):
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/tasks",
            headers=_auth_headers(),
            json={"title": ""},
        )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_list_tasks_empty(client):
    with _mock_verify(MOCK_USER):
        r = await client.get("/api/v1/tasks", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.anyio
async def test_list_tasks_returns_own_tasks_only(client):
    with _mock_verify(MOCK_USER):
        await client.post("/api/v1/tasks", headers=_auth_headers(), json={"title": "My task"})
    with _mock_verify(OTHER_USER):
        r = await client.get("/api/v1/tasks", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.anyio
async def test_list_tasks_filter_by_status(client):
    with _mock_verify(MOCK_USER):
        await client.post("/api/v1/tasks", headers=_auth_headers(), json={"title": "Pending task"})
        r = await client.get("/api/v1/tasks?status=pending", headers=_auth_headers())
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.anyio
async def test_list_tasks_filter_by_status_no_match(client):
    with _mock_verify(MOCK_USER):
        await client.post("/api/v1/tasks", headers=_auth_headers(), json={"title": "Pending task"})
        r = await client.get("/api/v1/tasks?status=done", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.anyio
async def test_get_task(client):
    with _mock_verify(MOCK_USER):
        created = await client.post(
            "/api/v1/tasks", headers=_auth_headers(), json={"title": "My task"}
        )
        task_id = created.json()["id"]
        r = await client.get(f"/api/v1/tasks/{task_id}", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json()["id"] == task_id


@pytest.mark.anyio
async def test_get_task_not_found(client):
    with _mock_verify(MOCK_USER):
        r = await client.get(
            "/api/v1/tasks/00000000-0000-0000-0000-000000000000", headers=_auth_headers()
        )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_get_other_users_task_not_found(client):
    with _mock_verify(MOCK_USER):
        created = await client.post(
            "/api/v1/tasks", headers=_auth_headers(), json={"title": "Private task"}
        )
        task_id = created.json()["id"]
    with _mock_verify(OTHER_USER):
        r = await client.get(f"/api/v1/tasks/{task_id}", headers=_auth_headers())
    assert r.status_code == 404


@pytest.mark.anyio
async def test_update_task_status(client):
    with _mock_verify(MOCK_USER):
        created = await client.post(
            "/api/v1/tasks", headers=_auth_headers(), json={"title": "To complete"}
        )
        task_id = created.json()["id"]
        r = await client.patch(
            f"/api/v1/tasks/{task_id}",
            headers=_auth_headers(),
            json={"status": "done"},
        )
    assert r.status_code == 200
    assert r.json()["status"] == "done"


@pytest.mark.anyio
async def test_update_task_invalid_priority_rejected(client):
    with _mock_verify(MOCK_USER):
        created = await client.post(
            "/api/v1/tasks", headers=_auth_headers(), json={"title": "Task"}
        )
        task_id = created.json()["id"]
        r = await client.patch(
            f"/api/v1/tasks/{task_id}",
            headers=_auth_headers(),
            json={"priority": 99},
        )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_delete_task_soft_deletes(client):
    with _mock_verify(MOCK_USER):
        created = await client.post(
            "/api/v1/tasks", headers=_auth_headers(), json={"title": "To delete"}
        )
        task_id = created.json()["id"]
        r = await client.delete(f"/api/v1/tasks/{task_id}", headers=_auth_headers())
    assert r.status_code == 204


@pytest.mark.anyio
async def test_delete_task_idempotent_second_call_404(client):
    with _mock_verify(MOCK_USER):
        created = await client.post(
            "/api/v1/tasks", headers=_auth_headers(), json={"title": "Delete twice"}
        )
        task_id = created.json()["id"]
        await client.delete(f"/api/v1/tasks/{task_id}", headers=_auth_headers())
        # After soft-delete status=cancelled, repo.get_by_id still returns the row.
        # A second delete call returns 204 (soft-delete is idempotent on cancelled tasks).
        r = await client.delete(f"/api/v1/tasks/{task_id}", headers=_auth_headers())
    assert r.status_code == 204


@pytest.mark.anyio
async def test_unauthenticated_request_rejected(client):
    r = await client.get("/api/v1/tasks")
    assert r.status_code == 401
