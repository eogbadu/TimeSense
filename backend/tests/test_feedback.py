from __future__ import annotations

from unittest.mock import patch

import pytest

from app.core.security import TokenUser

MOCK_USER = TokenUser(uid="uid-fb-1", email="fb@example.com", role="user", email_verified=True)
OTHER_USER = TokenUser(uid="uid-fb-2", email="fb-other@example.com", role="user", email_verified=True)


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


async def _create_task(client, user: TokenUser, title: str = "Test task") -> str:
    with _mock_verify(user):
        r = await client.post(
            "/api/v1/tasks",
            headers=_auth_headers(),
            json={"title": title, "source": "manual"},
        )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.mark.anyio
async def test_feedback_not_now(client):
    task_id = await _create_task(client, MOCK_USER)
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/recommendations/feedback",
            headers=_auth_headers(),
            json={"task_id": task_id, "signal": "not_now"},
        )
    assert r.status_code == 201
    data = r.json()
    assert data["signal"] == "not_now"
    assert "id" in data


@pytest.mark.anyio
async def test_feedback_done_marks_task_done(client):
    task_id = await _create_task(client, MOCK_USER, "Finish report")
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/recommendations/feedback",
            headers=_auth_headers(),
            json={"task_id": task_id, "signal": "done"},
        )
    assert r.status_code == 201
    # Verify task is now done
    with _mock_verify(MOCK_USER):
        task_r = await client.get(f"/api/v1/tasks/{task_id}", headers=_auth_headers())
    assert task_r.status_code == 200
    assert task_r.json()["status"] == "done"


@pytest.mark.anyio
async def test_feedback_snooze_stores_snooze_until(client):
    task_id = await _create_task(client, MOCK_USER)
    snooze_time = "2026-07-04T18:00:00Z"
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/recommendations/feedback",
            headers=_auth_headers(),
            json={"task_id": task_id, "signal": "snooze", "snooze_until": snooze_time},
        )
    assert r.status_code == 201
    assert r.json()["signal"] == "snooze"


@pytest.mark.anyio
async def test_feedback_agree_accepted(client):
    task_id = await _create_task(client, MOCK_USER)
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/recommendations/feedback",
            headers=_auth_headers(),
            json={"task_id": task_id, "signal": "agree"},
        )
    assert r.status_code == 201
    assert r.json()["signal"] == "agree"


@pytest.mark.anyio
async def test_feedback_disagree_accepted(client):
    task_id = await _create_task(client, MOCK_USER)
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/recommendations/feedback",
            headers=_auth_headers(),
            json={"task_id": task_id, "signal": "disagree"},
        )
    assert r.status_code == 201
    assert r.json()["signal"] == "disagree"


@pytest.mark.anyio
async def test_feedback_wrong_task_404(client):
    import uuid
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/recommendations/feedback",
            headers=_auth_headers(),
            json={"task_id": str(uuid.uuid4()), "signal": "not_now"},
        )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_feedback_other_users_task_404(client):
    task_id = await _create_task(client, OTHER_USER, "Other user task")
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/recommendations/feedback",
            headers=_auth_headers(),
            json={"task_id": task_id, "signal": "not_now"},
        )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_feedback_invalid_signal(client):
    task_id = await _create_task(client, MOCK_USER)
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/recommendations/feedback",
            headers=_auth_headers(),
            json={"task_id": task_id, "signal": "dismiss"},
        )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_feedback_unauthenticated(client):
    import uuid
    r = await client.post(
        "/api/v1/recommendations/feedback",
        json={"task_id": str(uuid.uuid4()), "signal": "not_now"},
    )
    assert r.status_code == 401
