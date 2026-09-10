"""Enhanced TranscriptProvider interface for the Transcript Reliability Engine.

All transcript providers (YouTube captions, Whisper, Deepgram, AssemblyAI, etc.)
implement this interface. Business logic never calls provider SDKs directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from models.transcript import TranscriptResult
from transcript_reliability.constants import ProviderCapability
from transcript_reliability.models import ProviderHealth, ProviderInfo


class TranscriptProvider(ABC):
    """Abstract interface for all transcript providers.

    Every provider implements this interface, enabling the Provider Manager
    to discover, route, failover, and monitor providers without knowing
    their implementation details.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for this provider (e.g. 'youtube_manual', 'deepgram')."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable display name (e.g. 'YouTube Manual Captions')."""
        ...

    @abstractmethod
    def get_transcript(
        self, video_id: str, language: str | None = None, **options: Any
    ) -> TranscriptResult:
        """Retrieve or generate a transcript for the given video.

        Args:
            video_id: 11-character YouTube video ID.
            language: Optional ISO language code hint (e.g. 'en', 'hi').
            **options: Provider-specific options (e.g. model_size, audio_format).

        Returns:
            ``TranscriptResult`` with segments and metadata.

        Raises:
            TranscriptUnavailableError: No transcript available from this provider.
            TranscriptFetchError: Network or API failure.
            TranscriptionError: Speech-to-text failure.
            ProviderAuthError: Authentication failure.
            ProviderQuotaError: Quota exceeded.
            ProviderTimeoutError: Request timed out.
        """
        ...

    @abstractmethod
    def health_check(self) -> ProviderHealth:
        """Check provider availability and return current health."""
        ...

    @abstractmethod
    def capabilities(self) -> list[ProviderCapability]:
        """Return the capabilities this provider supports."""
        ...

    @abstractmethod
    def info(self) -> ProviderInfo:
        """Return metadata about this provider."""
        ...

    @abstractmethod
    def cost_per_minute(self) -> float:
        """Return the cost per minute of audio for this provider (USD)."""
        ...

    @abstractmethod
    def supports_language(self, language: str) -> bool:
        """Check if this provider supports a specific language."""
        ...
