"""
LLM Provider abstraction — all AI features use this interface.
Swap providers by changing LLM_DEFAULT_PROVIDER in settings.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMRequest:
    prompt: str
    system: str = "You are a helpful personal time assistant."
    model: str = ""
    max_tokens: int = 1024
    temperature: float = 0.7
    metadata: dict = field(default_factory=dict)


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0


class LLMProvider(ABC):
    """Abstract base — implement this to add a new LLM provider."""

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send a completion request and return the response."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier, e.g. 'openai', 'anthropic'."""

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model identifier for this provider."""
