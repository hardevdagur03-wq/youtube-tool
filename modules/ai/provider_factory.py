"""Provider factory — Phase 7. Switching providers = config change only."""

from __future__ import annotations
import logging

from modules.ai.provider import LLMProvider, ProviderConfig
from modules.ai.gemini_provider import GeminiProvider
from modules.ai.openai_provider import OpenAIProvider
from modules.ai.claude_provider import ClaudeProvider

logger = logging.getLogger(__name__)

REGISTRY = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
}

DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o",
    "claude": "claude-3-sonnet",
}


def create(
    provider_name: str = "gemini",
    api_key: str = "",
    model: str | None = None,
    temperature: float = 0.2,
    max_output_tokens: int = 8192,
) -> LLMProvider:
    cls = REGISTRY.get(provider_name.lower())
    if cls is None:
        raise ValueError(f"Unsupported provider '{provider_name}'. Supported: {', '.join(REGISTRY)}")
    config = ProviderConfig(
        api_key=api_key,
        model=model or DEFAULT_MODELS.get(provider_name.lower(), ""),
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        extra={"provider": provider_name.lower()},
    )
    return cls(config)
