"""Provider Priority Manager — env-driven priority ordering of providers.

Supports default priority order, language-specific overrides, and
dynamic filtering based on health and circuit breaker state.
"""

from __future__ import annotations

import logging
from typing import Any

from transcript_reliability.config import TranscriptReliabilityConfig
from transcript_reliability.constants import ProviderStatus
from transcript_reliability.exceptions import ProviderNotFoundError
from transcript_reliability.interfaces.provider import TranscriptProvider
from transcript_reliability.provider_registry import ProviderRegistry
from transcript_reliability.health_monitor import HealthMonitor
from transcript_reliability.circuit_breaker import CircuitBreakerManager

logger = logging.getLogger(__name__)


class PriorityManager:
    """Manages provider priority ordering based on configuration.

    Priority is determined by:
    1. Language-specific override (if configured for the detected language)
    2. Default priority order from config
    3. Health status (unhealthy providers are deprioritized)
    4. Circuit breaker state (open providers are skipped)
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

    def get_priority_order(
        self,
        language: str | None = None,
        skip_unhealthy: bool = True,
        skip_open_circuit: bool = True,
    ) -> list[str]:
        """Get provider IDs in priority order for the given language.

        Args:
            language: Optional language code for language-specific priority.
            skip_unhealthy: If True, skip providers marked as UNHEALTHY.
            skip_open_circuit: If True, skip providers with open circuit breaker.

        Returns:
            List of provider IDs in priority order.
        """
        priority = self._config.get_priority_for_language(language or "")
        result = []

        for pid in priority:
            if not self._config.is_provider_enabled(pid):
                continue
            try:
                self._registry.get(pid)
            except ProviderNotFoundError:
                continue
            if skip_open_circuit:
                cb = self._circuit_breaker.get_state(pid)
                if cb.state.value == "open":
                    continue
            if skip_unhealthy:
                health = self._health.get_health(pid)
                if health.status == ProviderStatus.UNHEALTHY:
                    continue
            result.append(pid)

        # Fallback: include all registered providers not in priority list
        all_registered = self._registry.list_enabled(language=language)
        for provider in all_registered:
            pid = provider.provider_id
            if pid not in result:
                if skip_open_circuit:
                    cb = self._circuit_breaker.get_state(pid)
                    if cb.state.value == "open":
                        continue
                if skip_unhealthy:
                    health = self._health.get_health(pid)
                    if health.status == ProviderStatus.UNHEALTHY:
                        continue
                result.append(pid)

        return result

    def get_providers_in_order(
        self,
        language: str | None = None,
        skip_unhealthy: bool = True,
        skip_open_circuit: bool = True,
    ) -> list[TranscriptProvider]:
        """Get provider instances in priority order."""
        ordered_ids = self.get_priority_order(
            language=language,
            skip_unhealthy=skip_unhealthy,
            skip_open_circuit=skip_open_circuit,
        )
        providers = []
        for pid in ordered_ids:
            try:
                providers.append(self._registry.get(pid))
            except ProviderNotFoundError:
                continue
        return providers

    def get_priority_for_language(self, language: str) -> list[str]:
        """Get the priority order for a specific language without filtering."""
        return self._config.get_priority_for_language(language)

    def set_priority_order(self, provider_ids: list[str]) -> None:
        """Override the default priority order at runtime.

        Args:
            provider_ids: List of provider IDs in desired priority order.
        """
        self._config.provider_priority_order = list(provider_ids)
        logger.info("Priority order updated: %s", provider_ids)

    def set_language_override(self, language: str, provider_ids: list[str]) -> None:
        """Set a language-specific priority override.

        Args:
            language: ISO language code (e.g. 'hi', 'es').
            provider_ids: Provider IDs in desired priority order for this language.
        """
        self._config.provider_language_overrides[language] = list(provider_ids)
        logger.info("Language override for '%s': %s", language, provider_ids)
