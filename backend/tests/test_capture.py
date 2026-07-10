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


# ── Input validation & hygiene (TIME-189) ─────────────────────────────────────

def test_capture_request_cleans_and_collapses_raw_input():
    from app.api.v1.capture import CaptureRequest
    req = CaptureRequest(raw_input="  call   the\n\n dentist  ")
    assert req.raw_input == "call the dentist"


def test_capture_request_rejects_whitespace_only():
    from pydantic import ValidationError
    from app.api.v1.capture import CaptureRequest
    with pytest.raises(ValidationError):
        CaptureRequest(raw_input="    \t\n ")


def test_capture_request_invalid_timezone_falls_back_to_utc():
    from app.api.v1.capture import CaptureRequest
    assert CaptureRequest(raw_input="x", user_timezone="Not/AZone").user_timezone == "UTC"
    assert CaptureRequest(raw_input="x", user_timezone="America/New_York").user_timezone == "America/New_York"


def test_capture_request_unknown_type_hint_ignored():
    from app.api.v1.capture import CaptureRequest
    assert CaptureRequest(raw_input="x", type_hint="banana").type_hint is None
    assert CaptureRequest(raw_input="x", type_hint="Errand").type_hint == "errand"


def test_capture_request_lat_lng_range():
    from pydantic import ValidationError
    from app.api.v1.capture import CaptureRequest
    with pytest.raises(ValidationError):
        CaptureRequest(raw_input="x", location_lat=200.0)
    with pytest.raises(ValidationError):
        CaptureRequest(raw_input="x", location_lng=-999.0)
    ok = CaptureRequest(raw_input="x", location_lat=40.7, location_lng=-73.9)
    assert ok.location_lat == 40.7


def test_capture_request_date_sanity_and_precedence():
    from datetime import datetime, timezone
    from pydantic import ValidationError
    from app.api.v1.capture import CaptureRequest
    with pytest.raises(ValidationError):
        CaptureRequest(raw_input="x", scheduled_at=datetime(3999, 1, 1, tzinfo=timezone.utc))
    # Both set → the more specific scheduled_at wins; due_at is dropped.
    req = CaptureRequest(
        raw_input="x",
        scheduled_at=datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc),
        due_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    assert req.due_at is None


@pytest.mark.anyio
async def test_capture_out_of_range_lat_returns_422(client):
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/capture",
            headers=_auth_headers(),
            json={"raw_input": "buy milk", "location_lat": 200},
        )
    assert r.status_code == 422


# ── LLM-output safety (TIME-191): never trust the model's structured output ────

class _StubGateway:
    """A gateway whose complete_simple returns fixed JSON — used to feed hostile LLM output."""

    def __init__(self, payload: dict):
        self._text = json.dumps(payload)

    async def complete_simple(self, prompt: str, system: str, max_tokens: int) -> str:
        return self._text


@pytest.mark.anyio
async def test_capture_service_clamps_absurd_minutes():
    from app.services.capture_service import CaptureService
    gw = _StubGateway({"title": "Do a thing", "estimated_minutes": 999999, "priority": 3})
    tc = await CaptureService(gw).parse("do a thing")
    assert tc.estimated_minutes == 1440


@pytest.mark.anyio
async def test_capture_service_nulls_absurd_dates():
    from app.services.capture_service import CaptureService
    gw = _StubGateway({"title": "Do a thing", "scheduled_start": "3000-01-01T09:00:00Z", "priority": 3})
    tc = await CaptureService(gw).parse("do a thing")
    assert tc.scheduled_start is None


@pytest.mark.anyio
async def test_capture_service_cleans_blank_title():
    from app.services.capture_service import CaptureService
    gw = _StubGateway({"title": "   ", "priority": 3})
    tc = await CaptureService(gw).parse("call the dentist")
    assert tc.title.strip() != ""
