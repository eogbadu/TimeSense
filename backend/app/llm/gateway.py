"""
LLM Gateway — the single entry point for all AI completions in TimeSense.
Feature code calls gateway.complete() and never imports a provider directly.
"""

from fastapi import HTTPException, status

from app.core.config import settings
from app.llm.base import LLMProvider, LLMRequest, LLMResponse


class LLMGateway:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    @property
    def provider_name(self) -> str:
        return self._provider.name

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send a completion to the configured LLM provider."""
        return await self._provider.complete(request)

    async def complete_simple(
        self,
        prompt: str,
        system: str = "You are a helpful personal time assistant.",
        max_tokens: int = 1024,
    ) -> str:
        """Convenience wrapper returning just the content string."""
        response = await self.complete(LLMRequest(prompt=prompt, system=system, max_tokens=max_tokens))
        return response.content


def _build_gateway() -> LLMGateway:
    """Construct the gateway from current settings. Called once at startup."""
    provider_name = settings.llm_default_provider.lower()

    if provider_name == "openai":
        from app.llm.providers.openai_provider import OpenAIProvider
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_DEFAULT_PROVIDER=openai")
        provider = OpenAIProvider(
            api_key=settings.openai_api_key,
            default_model=settings.llm_default_model,
        )
    else:
        raise RuntimeError(f"Unknown LLM provider: '{provider_name}'. Supported: openai")

    return LLMGateway(provider=provider)


# Module-level singleton — rebuilt if settings change (tests can swap provider directly)
_gateway: LLMGateway | None = None


def get_llm_gateway() -> LLMGateway:
    """FastAPI dependency — returns the shared LLM gateway instance."""
    global _gateway
    if _gateway is None:
        try:
            _gateway = _build_gateway()
        except RuntimeError:
            # In development / test without API key, return a no-op gateway
            _gateway = LLMGateway(provider=_NoOpProvider())
    return _gateway


def set_llm_gateway(gateway: LLMGateway) -> None:
    """Test helper — swap the gateway with a mock."""
    global _gateway
    _gateway = gateway


class _NoOpProvider(LLMProvider):
    """Fallback used in dev/test when no API key is configured."""

    @property
    def name(self) -> str:
        return "noop"

    @property
    def default_model(self) -> str:
        return "noop"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM provider not configured. Set OPENAI_API_KEY in environment.",
        )
