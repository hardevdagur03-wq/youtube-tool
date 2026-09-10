"""Abstract LLM provider interface — Phase 7.

All blog generation logic MUST depend only on this abstraction.
Switching providers = configuration change only.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    cost_estimate: float = 0.0


@dataclass
class ProviderConfig:
    api_key: str = ""
    model: str = ""
    temperature: float = 0.2
    max_output_tokens: int = 8192
    timeout_secs: int = 120
    max_retries: int = 3
    base_url: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """Abstract base for all LLM providers."""

    def __init__(self, config: ProviderConfig | None = None) -> None:
        self.config = config or ProviderConfig()

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        ...

    @abstractmethod
    def generate_json(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        ...

    async def generate_stream(
        self, prompt: str, system_prompt: str | None = None,
    ) -> AsyncGenerator[str, None]:
        yield self.generate(prompt, system_prompt).text

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...
