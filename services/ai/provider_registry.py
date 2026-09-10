"""Provider Registry — extensible AI provider system.

Follows Open/Closed Principle: add new providers without modifying existing code.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from providers.llm_provider import LLMProvider, ProviderConfig

logger = logging.getLogger(__name__)


class RoutingStrategy(str, enum.Enum):
    LOWEST_COST = "lowest_cost"
    HIGHEST_QUALITY = "highest_quality"
    FASTEST_RESPONSE = "fastest_response"
    PROVIDER_PREFERENCE = "provider_preference"
    FALLBACK = "fallback"
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"


@dataclass
class ProviderMetadata:
    name: str
    models: list[str]
    capabilities: list[str]
    default_model: str
    priority: int = 100
    cost_multiplier: float = 1.0
    quality_score: float = 0.8
    avg_latency_ms: float = 1000.0
    is_available: bool = True


_PROVIDER_METADATA: dict[str, ProviderMetadata] = {
    "gemini": ProviderMetadata(
        name="gemini",
        models=["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
        capabilities=["text", "json", "vision", "streaming"],
        default_model="gemini-2.5-flash",
        priority=1,
        cost_multiplier=0.5,
        quality_score=0.85,
        avg_latency_ms=800,
    ),
    "openai": ProviderMetadata(
        name="openai",
        models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        capabilities=["text", "json", "vision", "streaming", "function_calling"],
        default_model="gpt-4o-mini",
        priority=2,
        cost_multiplier=1.5,
        quality_score=0.9,
        avg_latency_ms=1200,
    ),
    "anthropic": ProviderMetadata(
        name="anthropic",
        models=["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
        capabilities=["text", "json", "vision", "streaming"],
        default_model="claude-3-haiku",
        priority=3,
        cost_multiplier=2.0,
        quality_score=0.92,
        avg_latency_ms=1500,
    ),
    "mock": ProviderMetadata(
        name="mock",
        models=["mock-v1"],
        capabilities=["text", "json"],
        default_model="mock-v1",
        priority=999,
        cost_multiplier=0.0,
        quality_score=0.5,
        avg_latency_ms=10,
    ),
}


class ProviderRegistry:
    """Registry of AI providers for dynamic routing and failover.

    New providers register themselves without modifying existing code.
    """

    _providers: dict[str, type[LLMProvider]] = {}
    _instances: dict[str, LLMProvider] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[LLMProvider]) -> None:
        cls._providers[name] = provider_class
        logger.info("Provider registered: %s -> %s", name, provider_class.__name__)

    @classmethod
    def get_provider_class(cls, name: str) -> type[LLMProvider]:
        if name not in cls._providers:
            raise ValueError(f"Unknown provider: {name}. Available: {list(cls._providers.keys())}")
        return cls._providers[name]

    @classmethod
    def get_or_create(
        cls, name: str, config: ProviderConfig | None = None
    ) -> LLMProvider:
        cache_key = f"{name}:{config.model if config else 'default'}" if config else name
        if cache_key in cls._instances:
            return cls._instances[cache_key]

        provider_class = cls.get_provider_class(name)
        instance = provider_class(config)
        cls._instances[cache_key] = instance
        return instance

    @classmethod
    def list_providers(cls) -> list[str]:
        return list(cls._providers.keys())

    @classmethod
    def get_metadata(cls, name: str) -> ProviderMetadata | None:
        return _PROVIDER_METADATA.get(name)

    @classmethod
    def get_all_metadata(cls) -> dict[str, ProviderMetadata]:
        return dict(_PROVIDER_METADATA)

    @classmethod
    def resolve_provider(
        cls,
        task: str = "text",
        preferred_provider: str | None = None,
        strategy: RoutingStrategy = RoutingStrategy.FASTEST_RESPONSE,
    ) -> tuple[str, ProviderConfig]:
        if preferred_provider and preferred_provider in cls._providers:
            meta = _PROVIDER_METADATA.get(preferred_provider)
            config = ProviderConfig(
                model=(meta.default_model if meta else ""),
                extra={"provider": preferred_provider},
            )
            return preferred_provider, config

        available = [
            (name, meta)
            for name, meta in _PROVIDER_METADATA.items()
            if name in cls._providers and name != "mock"
            and task in meta.capabilities
        ]

        if not available:
            meta = _PROVIDER_METADATA.get("mock")
            return "mock", ProviderConfig(
                model=(meta.default_model if meta else "mock-v1"),
                extra={"provider": "mock"},
            )

        if strategy == RoutingStrategy.FASTEST_RESPONSE:
            available.sort(key=lambda x: x[1].avg_latency_ms)
        elif strategy == RoutingStrategy.LOWEST_COST:
            available.sort(key=lambda x: x[1].cost_multiplier)
        elif strategy == RoutingStrategy.HIGHEST_QUALITY:
            available.sort(key=lambda x: -x[1].quality_score)
        elif strategy == RoutingStrategy.PROVIDER_PREFERENCE:
            available.sort(key=lambda x: x[1].priority)

        best = available[0]
        return best[0], ProviderConfig(
            model=best[1].default_model,
            extra={"provider": best[0]},
        )

    @classmethod
    def clear(cls) -> None:
        cls._providers.clear()
        cls._instances.clear()
