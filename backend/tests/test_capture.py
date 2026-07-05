"""Capture endpoint tests — LLM gateway is always mocked, no real API calls."""
import json
from unittest.mock import patch

import pytest

from app.core.security import TokenUser
from app.llm.base import LLMResponse
from app.llm.gateway import LLMGateway, set_llm_gateway

MOCK_USER = TokenUser(
    uid="uid-capture-1", email="capture@example.com", role="user", email_verified=True
)


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


class _MockProvider:
    def __init__(self, response_json: dict):
        self._json = response_json

    @property
    def name(self) -> str:
        return "mock"

    @property
    def default_model(self) -> str:
        return "mock-model"

    async def complete(self, request):
        return LLMResponse(
            content=json.dumps(self._json),
            model="mock-model",
            provider="mock",
        )


def _use_mock_gateway(response_json: dict):
    from app.llm.gateway import LLMGateway

    set_llm_gateway(LLMGateway(provider=_MockProvider(response_json)))


@pytest.fixture(autouse=True)
def reset_gateway():
    yield
    set_llm_gateway(None)  # type: ignore[arg-type]  — resets to None so next test rebuilds


@pytest.mark.anyio
async def test_capture_creates_task(client):
    _use_mock_gateway({"title": "Call dentist", "estimated_minutes": 15, "due_at": None, "priority": 3})
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/capture",
            headers=_auth_headers(),
            json={"raw_input": "call dentist tomorrow at 2pm"},
        )
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Call dentist"
    assert data["estimated_minutes"] == 15
    assert data["source"] == "capture"
    assert data["raw_input"] == "call dentist tomorrow at 2pm"


@pytest.mark.anyio
async def test_capture_with_due_at(client):
    _use_mock_gateway({
        "title": "Submit report",
        "estimated_minutes": 60,
        "due_at": "2026-07-05T17:00:00+00:00",
        "priority": 2,
    })
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/capture",
            headers=_auth_headers(),
            json={"raw_input": "submit the quarterly report by Friday 5pm"},
        )
    assert r.status_code == 201
    data = r.json()
    assert data["priority"] == 2
    assert data["due_at"] is not None


@pytest.mark.anyio
async def test_capture_fallback_on_llm_error(client):
    from app.llm.gateway import LLMGateway, _NoOpProvider

    set_llm_gateway(LLMGateway(provider=_NoOpProvider()))
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/capture",
            headers=_auth_headers(),
            json={"raw_input": "buy groceries"},
        )
    # fallback: raw_input becomes the title, task is still created
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Buy groceries"
    assert data["source"] == "capture"


@pytest.mark.anyio
async def test_capture_fallback_on_invalid_json(client):
    class _BrokenProvider:
        @property
        def name(self):
            return "broken"

        @property
        def default_model(self):
            return "broken"

        async def complete(self, request):
            return LLMResponse(content="not valid json", model="broken", provider="broken")

    from app.llm.gateway import LLMGateway

    set_llm_gateway(LLMGateway(provider=_BrokenProvider()))
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/capture",
            headers=_auth_headers(),
            json={"raw_input": "pick up prescription"},
        )
    assert r.status_code == 201
    assert r.json()["title"] == "Pick up prescription"


@pytest.mark.anyio
async def test_capture_empty_input_rejected(client):
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/capture",
            headers=_auth_headers(),
            json={"raw_input": ""},
        )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_capture_unauthenticated_rejected(client):
    r = await client.post("/api/v1/capture", json={"raw_input": "test"})
    assert r.status_code == 401
