"""Provider implementations for the Transcript Reliability Engine.

All providers implement the ``TranscriptProvider`` interface.
Business logic never calls provider SDKs directly.
"""

from __future__ import annotations

from transcript_reliability.interfaces.provider import TranscriptProvider
from transcript_reliability.providers.base import BaseTranscriptProvider
from transcript_reliability.providers.youtube_manual import YouTubeManualProvider
from transcript_reliability.providers.youtube_auto import YouTubeAutoProvider
from transcript_reliability.providers.whisper_local import WhisperLocalProvider
from transcript_reliability.providers.whisper_api import WhisperAPIProvider
from transcript_reliability.providers.deepgram import DeepgramProvider
from transcript_reliability.providers.assemblyai import AssemblyAIProvider
from transcript_reliability.providers.plugin import discover_plugins

__all__ = [
    "BaseTranscriptProvider",
    "YouTubeManualProvider",
    "YouTubeAutoProvider",
    "WhisperLocalProvider",
    "WhisperAPIProvider",
    "DeepgramProvider",
    "AssemblyAIProvider",
    "discover_plugins",
]

_PROVIDER_CLASSES = [
    YouTubeManualProvider,
    YouTubeAutoProvider,
    WhisperLocalProvider,
    WhisperAPIProvider,
    DeepgramProvider,
    AssemblyAIProvider,
]


def get_default_providers() -> list[TranscriptProvider]:
    """Get instances of all built-in providers.

    Each provider checks its own API key/config and raises
    only if configured and failing. Missing API keys result
    in graceful degradation (provider claims no capability).
    """
    providers = [cls() for cls in _PROVIDER_CLASSES]
    return providers


def get_default_provider_map() -> dict[str, TranscriptProvider]:
    """Get a dict mapping provider_id to provider instance."""
    return {p.provider_id: p for p in get_default_providers()}
