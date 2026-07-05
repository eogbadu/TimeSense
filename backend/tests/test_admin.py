from unittest.mock import patch

import pytest

from app.core.security import TokenUser
from app.models.calendar import CalendarIntegration
from app.models.recommendation_feedback import RecommendationFeedback
from app.repositories.invite_repository import InviteCodeRepository, WaitlistRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.task_repository import TaskRepository
from app.services.user_service import UserService

ADMIN_USER = TokenUser(uid="uid-admin-1", email="admin@timesense.app", role="admin", email_verified=True)
NORMAL_USER = TokenUser(uid="uid-normal-1", email="user@example.com", role="user", email_verified=True)
OTHER_USER = TokenUser(uid="uid-normal-2", email="other@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


@pytest.mark.anyio
async def test_admin_health_accessible_to_admin(client):
    with _mock_verify(ADMIN_USER):
        r = await client.get("/api/v1/admin/health", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


@pytest.mark.anyio
async def test_admin_health_forbidden_to_normal_user(client):
    with _mock_verify(NORMAL_USER):
        r = await client.get("/api/v1/admin/health", headers=_auth_headers())
    assert r.status_code == 403


@pytest.mark.anyio
async def test_admin_health_unauthenticated(client):
    r = await client.get("/api/v1/admin/health")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_admin_list_users(client):
    # Seed a normal user first
    with _mock_verify(NORMAL_USER):
        await client.get("/api/v1/users/me", headers=_auth_headers())

    with _mock_verify(ADMIN_USER):
        r = await client.get("/api/v1/admin/users", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert "users" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.anyio
async def test_admin_list_users_forbidden_to_normal_user(client):
    with _mock_verify(NORMAL_USER):
        r = await client.get("/api/v1/admin/users", headers=_auth_headers())
    assert r.status_code == 403


@pytest.mark.anyio
async def test_admin_list_users_pagination(client):
    with _mock_verify(ADMIN_USER):
        r = await client.get("/api/v1/admin/users?offset=0&limit=5", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["limit"] == 5
    assert data["offset"] == 0


@pytest.mark.anyio
async def test_admin_search_users_by_email(client):
    with _mock_verify(NORMAL_USER):
        await client.get("/api/v1/users/me", headers=_auth_headers())
    with _mock_verify(OTHER_USER):
        await client.get("/api/v1/users/me", headers=_auth_headers())

    with _mock_verify(ADMIN_USER):
        r = await client.get(
            f"/api/v1/admin/users?search={NORMAL_USER.email}", headers=_auth_headers()
        )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["users"][0]["email"] == NORMAL_USER.email


@pytest.mark.anyio
async def test_admin_list_subscriptions(client, db_session):
    user, _ = await UserService(db_session).get_or_create_user(NORMAL_USER.uid, NORMAL_USER.email)
    await SubscriptionRepository(db_session).start_trial(user.id)

    with _mock_verify(ADMIN_USER):
        r = await client.get("/api/v1/admin/subscriptions", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()["subscriptions"]
    assert any(s["email"] == NORMAL_USER.email and s["status"] == "trialing" for s in data)


@pytest.mark.anyio
async def test_admin_subscriptions_forbidden_to_normal_user(client):
    with _mock_verify(NORMAL_USER):
        r = await client.get("/api/v1/admin/subscriptions", headers=_auth_headers())
    assert r.status_code == 403


@pytest.mark.anyio
async def test_admin_list_feedback(client, db_session):
    user, _ = await UserService(db_session).get_or_create_user(NORMAL_USER.uid, NORMAL_USER.email)
    task = await TaskRepository(db_session).create(user_id=user.id, title="Write report")
    fb = RecommendationFeedback(user_id=user.id, task_id=task.id, signal="done")
    db_session.add(fb)
    await db_session.flush()

    with _mock_verify(ADMIN_USER):
        r = await client.get("/api/v1/admin/feedback", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()["feedback"]
    assert any(
        f["user_email"] == NORMAL_USER.email and f["task_title"] == "Write report" and f["signal"] == "done"
        for f in data
    )


@pytest.mark.anyio
async def test_admin_feedback_forbidden_to_normal_user(client):
    with _mock_verify(NORMAL_USER):
        r = await client.get("/api/v1/admin/feedback", headers=_auth_headers())
    assert r.status_code == 403


@pytest.mark.anyio
async def test_admin_integration_status(client, db_session):
    user, _ = await UserService(db_session).get_or_create_user(NORMAL_USER.uid, NORMAL_USER.email)
    db_session.add(
        CalendarIntegration(
            user_id=user.id, provider="google", access_token="tok", is_active=True
        )
    )
    await db_session.flush()

    with _mock_verify(ADMIN_USER):
        r = await client.get("/api/v1/admin/integrations", headers=_auth_headers())
    assert r.status_code == 200
    providers = {p["provider"]: p for p in r.json()["providers"]}
    assert providers["google"]["active_count"] >= 1


@pytest.mark.anyio
async def test_admin_integrations_forbidden_to_normal_user(client):
    with _mock_verify(NORMAL_USER):
        r = await client.get("/api/v1/admin/integrations", headers=_auth_headers())
    assert r.status_code == 403


@pytest.mark.anyio
async def test_admin_metrics(client, db_session):
    user, _ = await UserService(db_session).get_or_create_user(NORMAL_USER.uid, NORMAL_USER.email)
    await SubscriptionRepository(db_session).start_trial(user.id)
    await WaitlistRepository(db_session).add(email="waiting@example.com")
    await InviteCodeRepository(db_session).create(created_by_id=None, max_uses=1)

    with _mock_verify(ADMIN_USER):
        r = await client.get("/api/v1/admin/metrics", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["total_users"] >= 1
    assert data["trialing_subscriptions"] >= 1
    assert data["waitlist_count"] >= 1
    assert data["active_invite_codes"] >= 1


@pytest.mark.anyio
async def test_admin_metrics_forbidden_to_normal_user(client):
    with _mock_verify(NORMAL_USER):
        r = await client.get("/api/v1/admin/metrics", headers=_auth_headers())
    assert r.status_code == 403


@pytest.mark.anyio
async def test_admin_list_waitlist(client, db_session):
    await WaitlistRepository(db_session).add(email="waiting@example.com")

    with _mock_verify(ADMIN_USER):
        r = await client.get("/api/v1/admin/waitlist", headers=_auth_headers())
    assert r.status_code == 200
    assert any(e["email"] == "waiting@example.com" for e in r.json())


@pytest.mark.anyio
async def test_admin_waitlist_forbidden_to_normal_user(client):
    with _mock_verify(NORMAL_USER):
        r = await client.get("/api/v1/admin/waitlist", headers=_auth_headers())
    assert r.status_code == 403
