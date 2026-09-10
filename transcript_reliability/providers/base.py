"""Base Transcript Provider — shared logic for all provider implementations.

Provides common functionality for provider metadata, health checking,
capability reporting, and cost tracking.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from models.transcript import TranscriptResult
from transcript_reliability.constants import ProviderCapability, ProviderStatus, PROVIDER_COST_PER_MINUTE
from transcript_reliability.interfaces.provider import TranscriptProvider
from transcript_reliability.models import ProviderHealth, ProviderInfo

logger = logging.getLogger(__name__)


class BaseTranscriptProvider(TranscriptProvider):
    """Base class for all transcript providers.

    Subclasses must implement:
    - provider_id
    - name
    - get_transcript()
    - capabilities() (with the specific capabilities)
    """

    # Override in subclasses
    _provider_id: str = "base"
    _name: str = "Base Provider"
    _capabilities: list[ProviderCapability] = []
    _cost_per_minute: float = 0.0

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def name(self) -> str:
        return self._name

    def capabilities(self) -> list[ProviderCapability]:
        return list(self._capabilities)

    def info(self) -> ProviderInfo:
        return ProviderInfo(
            provider_id=self._provider_id,
            name=self._name,
            capabilities=self.capabilities(),
            cost_per_minute=self._cost_per_minute,
            enabled=True,
        )

    def cost_per_minute(self) -> float:
        return PROVIDER_COST_PER_MINUTE.get(self._provider_id, self._cost_per_minute)

    def health_check(self) -> ProviderHealth:
        """Default health check — subclass may override for real checks."""
        return ProviderHealth(
            provider_id=self._provider_id,
            status=ProviderStatus.HEALTHY,
        )

    def supports_language(self, language: str | None) -> bool:
        """Override if provider has specific language support."""
        if not language:
            return True
        # Most providers support English at minimum
        supported = {"en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko", "ar", "hi"}
        lang_base = language.split("-")[0].lower() if language else ""
        return lang_base in supported

    def get_transcript(
        self, video_id: str, language: str | None = None, **options: Any
    ) -> TranscriptResult:
        raise NotImplementedError("Subclasses must implement get_transcript()")
