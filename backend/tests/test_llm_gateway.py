"""Tests for LLM gateway abstraction — no real API calls."""
import pytest

from app.llm.base import LLMProvider, LLMRequest, LLMResponse
from app.llm.gateway import LLMGateway, get_llm_gateway, set_llm_gateway


class MockProvider(LLMProvider):
    def __init__(self, response_text: str = "mocked response") -> None:
        self._response = response_text
        self.calls: list[LLMRequest] = []

    @property
    def name(self) -> str:
        return "mock"

    @property
    def default_model(self) -> str:
        return "mock-model"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        return LLMResponse(
            content=self._response,
            model=self.default_model,
            provider=self.name,
            input_tokens=10,
            output_tokens=5,
        )


class ErrorProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "error"

    @property
    def default_model(self) -> str:
        return "error-model"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        from fastapi import HTTPException
        raise HTTPException(status_code=502, detail="Provider error")


@pytest.mark.anyio
async def test_gateway_complete_returns_content():
    mock = MockProvider("hello from AI")
    gateway = LLMGateway(provider=mock)
    result = await gateway.complete(LLMRequest(prompt="Say hello"))
    assert result.content == "hello from AI"
    assert result.provider == "mock"
    assert len(mock.calls) == 1


@pytest.mark.anyio
async def test_gateway_complete_simple_returns_string():
    gateway = LLMGateway(provider=MockProvider("simple response"))
    result = await gateway.complete_simple("What time is it?")
    assert result == "simple response"


@pytest.mark.anyio
async def test_gateway_passes_system_prompt():
    mock = MockProvider()
    gateway = LLMGateway(provider=mock)
    await gateway.complete(LLMRequest(prompt="test", system="Custom system"))
    assert mock.calls[0].system == "Custom system"


@pytest.mark.anyio
async def test_gateway_passes_max_tokens():
    mock = MockProvider()
    gateway = LLMGateway(provider=mock)
    await gateway.complete(LLMRequest(prompt="test", max_tokens=256))
    assert mock.calls[0].max_tokens == 256


@pytest.mark.anyio
async def test_set_gateway_replaces_singleton():
    mock = MockProvider("swapped")
    set_llm_gateway(LLMGateway(provider=mock))
    gw = get_llm_gateway()
    result = await gw.complete_simple("test")
    assert result == "swapped"


@pytest.mark.anyio
async def test_gateway_propagates_provider_error():
    gateway = LLMGateway(provider=ErrorProvider())
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await gateway.complete(LLMRequest(prompt="test"))
    assert exc_info.value.status_code == 502


@pytest.mark.anyio
async def test_noop_provider_returns_503(client):
    from app.llm.gateway import _NoOpProvider
    set_llm_gateway(LLMGateway(provider=_NoOpProvider()))
    gw = get_llm_gateway()
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await gw.complete(LLMRequest(prompt="test"))
    assert exc_info.value.status_code == 503
