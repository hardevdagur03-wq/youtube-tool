"""Provider Manager — handles provider lifecycle, configuration, and health.

Manages provider enable/disable, configuration, capability detection,
cost tracking, latency tracking, and success tracking.
"""

from __future__ import annotations

import logging
from typing import Any

from transcript_reliability.config import TranscriptReliabilityConfig
from transcript_reliability.constants import PROVIDER_COST_PER_MINUTE, ProviderCapability, ProviderStatus
from transcript_reliability.exceptions import ProviderNotFoundError
from transcript_reliability.interfaces.provider import TranscriptProvider
from transcript_reliability.models import ProviderHealth, ProviderInfo, ProviderStats
from transcript_reliability.provider_registry import ProviderRegistry
from transcript_reliability.health_monitor import HealthMonitor
from transcript_reliability.circuit_breaker import CircuitBreakerManager

logger = logging.getLogger(__name__)


class ProviderManager:
    """Manages provider lifecycle, configuration, and health tracking.

    Coordinates between ProviderRegistry, HealthMonitor, and CircuitBreakerManager.
    Provides a unified API for querying provider status and capabilities.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        health_monitor: HealthMonitor,
        circuit_breaker: CircuitBreakerManager,
        config: TranscriptReliabilityConfig | None = None,
    ) -> None:
        self._registry = registry
        self._health = health_monitor
        self._circuit_breaker = circuit_breaker
        self._config = config or TranscriptReliabilityConfig()

    def enable_provider(self, provider_id: str) -> None:
        """Enable a provider."""
        try:
            self._registry.get(provider_id)
        except ProviderNotFoundError:
            raise
        self._config.provider_disabled = [
            p for p in self._config.provider_disabled if p != provider_id
        ]
        logger.info("Provider enabled: %s", provider_id)

    def disable_provider(self, provider_id: str) -> None:
        """Disable a provider."""
        if provider_id not in self._config.provider_disabled:
            self._config.provider_disabled = list(self._config.provider_disabled) + [provider_id]
        logger.info("Provider disabled: %s", provider_id)

    def is_provider_enabled(self, provider_id: str) -> bool:
        """Check if a provider is enabled."""
        return self._config.is_provider_enabled(provider_id)

    def get_provider_info(self, provider_id: str) -> ProviderInfo:
        """Get detailed info about a provider."""
        provider = self._registry.get(provider_id)
        return provider.info()

    def get_provider_health(self, provider_id: str) -> ProviderHealth:
        """Get current health status for a provider."""
        return self._health.get_health(provider_id)

    def get_provider_stats(self, provider_id: str) -> ProviderStats:
        """Get aggregate statistics for a provider."""
        return self._health.get_stats(provider_id)

    def get_provider_status(self, provider_id: str) -> ProviderStatus:
        """Get the overall status for a provider."""
        health = self._health.get_health(provider_id)
        cb = self._circuit_breaker.get_state(provider_id)
        if cb.state.value == "open":
            return ProviderStatus.UNHEALTHY
        return health.status

    def list_providers(self) -> list[ProviderInfo]:
        """List all registered providers with info."""
        return self._registry.list_info()

    def list_healthy_providers(self, language: str | None = None) -> list[TranscriptProvider]:
        """List providers that are enabled, healthy, and have circuit breaker closed."""
        providers = self._registry.list_enabled(language=language)
        result = []
        for p in providers:
            pid = p.provider_id
            cb = self._circuit_breaker.get_state(pid)
            if cb.state.value == "open":
                continue
            health = self._health.get_health(pid)
            if health.status == ProviderStatus.UNHEALTHY:
                continue
            result.append(p)
        return result

    def get_capability_summary(self) -> dict[str, list[str]]:
        """Get a summary of what capabilities each provider offers."""
        summary: dict[str, list[str]] = {}
        for p in self._registry.list_all():
            summary[p.provider_id] = [c.value for c in p.capabilities()]
        return summary

    def get_cost_summary(self) -> dict[str, float]:
        """Get cost per minute for all providers."""
        costs: dict[str, float] = {}
        for p in self._registry.list_all():
            costs[p.provider_id] = PROVIDER_COST_PER_MINUTE.get(p.provider_id, 0.0)
        return costs

    def get_latency_summary(self) -> dict[str, dict[str, float]]:
        """Get latency statistics for all providers."""
        summary: dict[str, dict[str, float]] = {}
        for p in self._registry.list_all():
            health = self._health.get_health(p.provider_id)
            summary[p.provider_id] = {
                "avg_ms": health.avg_latency_ms,
                "p95_ms": health.p95_latency_ms,
                "p99_ms": health.p99_latency_ms,
            }
        return summary
