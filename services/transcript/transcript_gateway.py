"""Transcript Gateway — multi-provider transcript orchestration with routing and failover.

Routes transcript requests through a priority-ordered provider chain.
If a provider fails, automatically falls back to the next available provider.
"""

from __future__ import annotations

import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class TranscriptProviderName(str, enum.Enum):
    MANUAL = "manual"
    AUTO = "auto"
    WHISPER_API = "whisper_api"
    WHISPER_LOCAL = "whisper_local"
    HUMAN_UPLOAD = "human_upload"


@dataclass
class TranscriptProviderMetadata:
    name: str
    priority: int
    cost_multiplier: float = 1.0
    avg_latency_ms: float = 5000.0
    quality_score: float = 0.9
    languages: list[str] = field(default_factory=lambda: ["en"])


@dataclass
class TranscriptResult:
    success: bool = False
    video_id: str = ""
    text: str = ""
    segments: list[dict] = field(default_factory=list)
    language: str = ""
    provider: str = ""
    latency_ms: float = 0.0
    confidence: float = 0.0
    word_count: int = 0
    error: str = ""
    from_cache: bool = False


_PROVIDER_PRIORITY: list[TranscriptProviderMetadata] = [
    TranscriptProviderMetadata("manual", priority=1, quality_score=0.95),
    TranscriptProviderMetadata("auto", priority=2, quality_score=0.85),
    TranscriptProviderMetadata("whisper_api", priority=3, cost_multiplier=2.0, avg_latency_ms=30000),
    TranscriptProviderMetadata("whisper_local", priority=4, cost_multiplier=0.0, avg_latency_ms=120000),
    TranscriptProviderMetadata("human_upload", priority=5),
]


class TranscriptGateway:
    """Central gateway for transcript retrieval with automatic failover.

    Routes through provider chain: manual → auto → whisper → human_upload.
    """

    def __init__(self):
        self._providers: dict[str, Any] = {}

    def register_provider(self, name: str, provider: Any) -> None:
        self._providers[name] = provider
        logger.info("Transcript provider registered: %s", name)

    def get_transcript(
        self, video_id: str, language: str | None = None
    ) -> TranscriptResult:
        errors = []
        start = time.time()

        for meta in sorted(_PROVIDER_PRIORITY, key=lambda m: m.priority):
            if meta.name not in self._providers:
                continue

            provider = self._providers[meta.name]
            try:
                logger.info(
                    "Trying provider %s for video %s...",
                    meta.name, video_id,
                )
                result = provider.get_transcript(video_id, language)

                if result and getattr(result, "success", False):
                    elapsed = (time.time() - start) * 1000
                    segments = [
                        {
                            "start": getattr(s, "start", 0),
                            "end": getattr(s, "end", 0),
                            "text": getattr(s, "text", ""),
                        }
                        for s in getattr(result, "segments", [])
                    ]
                    text = getattr(result, "plain_text", "") or getattr(result, "text", "")
                    return TranscriptResult(
                        success=True,
                        video_id=video_id,
                        text=text,
                        segments=segments,
                        language=getattr(result, "language", language or ""),
                        provider=meta.name,
                        latency_ms=round(elapsed, 1),
                        confidence=meta.quality_score,
                        word_count=len(text.split()),
                    )

                errors.append(f"{meta.name}: No transcript available")

            except Exception as exc:
                logger.warning(
                    "Provider %s failed for %s: %s",
                    meta.name, video_id, exc,
                )
                errors.append(f"{meta.name}: {exc}")
                continue

        return TranscriptResult(
            success=False,
            video_id=video_id,
            error="All providers failed: " + "; ".join(errors),
        )

    def get_transcript_with_failover(
        self, video_id: str, language: str | None = None
    ) -> TranscriptResult:
        return self.get_transcript(video_id, language)
