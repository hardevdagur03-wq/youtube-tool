"""Provider Registry — dynamic provider registration and discovery.

Allows providers to be registered, discovered, and queried by capability
without business logic knowing provider implementations.
"""

from __future__ import annotations

import logging
from typing import Any

from transcript_reliability.constants import ProviderCapability
from transcript_reliability.exceptions import ProviderNotFoundError, ProviderDisabledError
from transcript_reliability.interfaces.provider import TranscriptProvider
from transcript_reliability.models import ProviderInfo
from transcript_reliability.config import TranscriptReliabilityConfig

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry of all available transcript providers.

    Providers register themselves here. The Provider Manager and
    Failover Engine query the registry for available providers.
    """

    def __init__(self, config: TranscriptReliabilityConfig | None = None) -> None:
        self._providers: dict[str, TranscriptProvider] = {}
        self._config = config or TranscriptReliabilityConfig()

    def register(self, provider: TranscriptProvider) -> None:
        """Register a provider instance.

        Args:
            provider: A TranscriptProvider implementation.
        """
        pid = provider.provider_id
        if pid in self._providers:
            logger.warning("Overwriting existing provider: %s", pid)
        self._providers[pid] = provider
        logger.info("Registered provider: %s (%s)", pid, provider.name)

    def unregister(self, provider_id: str) -> None:
        """Remove a provider from the registry.

        Args:
            provider_id: Unique provider identifier.
        """
        self._providers.pop(provider_id, None)
        logger.info("Unregistered provider: %s", provider_id)

    def get(self, provider_id: str) -> TranscriptProvider:
        """Get a provider by ID.

        Args:
            provider_id: Unique provider identifier.

        Returns:
            The registered provider instance.

        Raises:
            ProviderNotFoundError: If provider is not registered.
        """
        provider = self._providers.get(provider_id)
        if provider is None:
            raise ProviderNotFoundError(
                f"Provider '{provider_id}' not registered. "
                f"Available: {list(self._providers.keys())}"
            )
        return provider

    def get_enabled(self, provider_id: str, language: str | None = None) -> TranscriptProvider:
        """Get a provider only if it's enabled.

        Args:
            provider_id: Unique provider identifier.
            language: Optional language to check support.

        Returns:
            The registered provider instance.

        Raises:
            ProviderNotFoundError: If not registered.
            ProviderDisabledError: If disabled via config.
        """
        if not self._config.is_provider_enabled(provider_id):
            raise ProviderDisabledError(f"Provider '{provider_id}' is disabled via configuration")

        provider = self.get(provider_id)

        if language and not provider.supports_language(language):
            raise ProviderDisabledError(
                f"Provider '{provider_id}' does not support language '{language}'"
            )

        return provider

    def list_all(self) -> list[TranscriptProvider]:
        """List all registered providers."""
        return list(self._providers.values())

    def list_enabled(self, language: str | None = None) -> list[TranscriptProvider]:
        """List only enabled providers, optionally filtered by language support."""
        result = []
        for pid, provider in self._providers.items():
            if not self._config.is_provider_enabled(pid):
                continue
            if language and not provider.supports_language(language):
                continue
            result.append(provider)
        return result

    def list_by_capability(self, capability: ProviderCapability) -> list[TranscriptProvider]:
        """List providers that support a specific capability."""
        return [p for p in self._providers.values() if capability in p.capabilities()]

    def get_info(self, provider_id: str) -> ProviderInfo:
        """Get metadata about a provider."""
        provider = self.get(provider_id)
        return provider.info()

    def list_info(self) -> list[ProviderInfo]:
        """Get metadata for all registered providers."""
        return [p.info() for p in self._providers.values()]

    @property
    def count(self) -> int:
        return len(self._providers)

    @property
    def provider_ids(self) -> list[str]:
        return list(self._providers.keys())
