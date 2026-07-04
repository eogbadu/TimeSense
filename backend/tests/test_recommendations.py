from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock

import pytest

from app.core.security import TokenUser
from app.llm.gateway import _NoOpProvider, set_llm_gateway, get_llm_gateway

MOCK_USER = TokenUser(uid="uid-rec-1", email="rec@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify():
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={
            "uid": MOCK_USER.uid,
            "email": MOCK_USER.email,
            "role": MOCK_USER.role,
            "email_verified": MOCK_USER.email_verified,
        },
    )


class _MockProvider(_NoOpProvider):
    async def complete(self, request):
        from app.llm.gateway import LLMResponse
        return LLMResponse(content="This is your highest priority task right now.", model="mock")


@pytest.fixture(autouse=True)
def reset_gateway():
    import app.llm.gateway as _gw_mod
    original = _gw_mod._gateway
    set_llm_gateway(_MockProvider())
    yield
    _gw_mod._gateway = original


@pytest.mark.anyio
async def test_recommendations_authenticated(client):
    """Returns 200 with expected structure."""
    with _mock_verify():
        r = await client.get("/api/v1/recommendations", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert "best" in data
    assert "alternatives" in data
    assert "usable_minutes" in data


@pytest.mark.anyio
async def test_recommendations_no_tasks_best_is_null(client):
    """No tasks → best is null."""
    with _mock_verify():
        r = await client.get("/api/v1/recommendations", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json()["best"] is None
    assert r.json()["alternatives"] == []


@pytest.mark.anyio
async def test_recommendations_returns_best_task_with_why(client):
    """When tasks exist, best has task + why string."""
    today = datetime.now(timezone.utc).date().isoformat()
    with _mock_verify():
        await client.post(
            "/api/v1/tasks",
            headers=_auth_headers(),
            json={"title": "Write report", "priority": 1,
                  "scheduled_start": f"{today}T09:00:00Z", "source": "manual"},
        )
        r = await client.get("/api/v1/recommendations", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["best"]["task"]["title"] == "Write report"
    assert isinstance(data["best"]["why"], str)
    assert len(data["best"]["why"]) > 0


@pytest.mark.anyio
async def test_recommendations_alternatives_at_most_2(client):
    """At most 2 alternatives returned."""
    today = datetime.now(timezone.utc).date().isoformat()
    with _mock_verify():
        for i, p in enumerate([1, 2, 3, 4]):
            await client.post(
                "/api/v1/tasks",
                headers=_auth_headers(),
                json={"title": f"Task {i}", "priority": p,
                      "scheduled_start": f"{today}T0{8+i}:00:00Z", "source": "manual"},
            )
        r = await client.get("/api/v1/recommendations", headers=_auth_headers())
    assert r.status_code == 200
    assert len(r.json()["alternatives"]) <= 2


@pytest.mark.anyio
async def test_recommendations_llm_fallback_when_503(client):
    """Falls back to canned why string when LLM returns 503."""
    from app.llm.gateway import LLMGateway
    set_llm_gateway(LLMGateway(provider=_NoOpProvider()))  # NoOp raises 503
    today = datetime.now(timezone.utc).date().isoformat()
    with _mock_verify():
        await client.post(
            "/api/v1/tasks",
            headers=_auth_headers(),
            json={"title": "Emergency task", "priority": 1,
                  "scheduled_start": f"{today}T10:00:00Z", "source": "manual"},
        )
        r = await client.get("/api/v1/recommendations", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["best"] is not None
    assert isinstance(data["best"]["why"], str)  # fallback string present


@pytest.mark.anyio
async def test_recommendations_unauthenticated(client):
    r = await client.get("/api/v1/recommendations")
    assert r.status_code == 401
