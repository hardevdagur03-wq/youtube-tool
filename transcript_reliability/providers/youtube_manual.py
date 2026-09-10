"""YouTube Manual Captions Provider — Priority 1.

Retrieves official human-created YouTube captions via youtube-transcript-api.
"""

from __future__ import annotations

import logging
from typing import Any

from models.transcript import TranscriptResult, TranscriptSource, TranscriptProviderName
from transcript_reliability.constants import ProviderCapability
from transcript_reliability.providers.base import BaseTranscriptProvider
from utils.text_cleaner import TextCleaner
from utils.read_time import estimate_read_time

logger = logging.getLogger(__name__)

try:
    from clients.youtube_transcript_client import (
        YouTubeTranscriptClient,
        NoTranscriptFoundError,
        TranscriptsDisabledError,
        VideoUnavailableError,
        TooManyRequestsError,
    )
    _HAS_CLIENT = True
except ImportError:
    _HAS_CLIENT = False


class YouTubeManualProvider(BaseTranscriptProvider):
    """Priority 1: Official YouTube human-created captions."""

    _provider_id = "youtube_manual"
    _name = "YouTube Manual Captions"
    _capabilities = [ProviderCapability.CAPTIONS, ProviderCapability.LANGUAGE_DETECTION]
    _cost_per_minute = 0.0

    def __init__(self) -> None:
        self._client = YouTubeTranscriptClient() if _HAS_CLIENT else None
        self._text_cleaner = TextCleaner()

    def get_transcript(
        self, video_id: str, language: str | None = None, **options: Any
    ) -> TranscriptResult:
        result = TranscriptResult(
            video_id=video_id,
            source=TranscriptSource.MANUAL,
            provider=TranscriptProviderName.YOUTUBE_MANUAL,
        )

        if not _HAS_CLIENT or self._client is None:
            result.success = False
            result.error = "youtube-transcript-api is not installed. Install with: pip install youtube-transcript-api"
            return result

        try:
            preferred = [language] if language else None
            raw_segments, detected_lang, is_manual, translation_source = (
                self._client.find_best_transcript(
                    video_id,
                    preferred_languages=preferred,
                    transcript_type="manual",
                )
            )
        except NoTranscriptFoundError:
            result.success = False
            result.error = "No manual transcript available for this video"
            return result
        except TranscriptsDisabledError:
            result.success = False
            result.error = "Transcripts are disabled for this video"
            return result
        except VideoUnavailableError:
            result.success = False
            result.error = "Video is unavailable"
            return result
        except TooManyRequestsError:
            result.success = False
            result.error = "Rate limited by YouTube"
            return result
        except Exception as exc:
            result.success = False
            result.error = f"Manual transcript fetch failed: {exc}"
            return result

        if not raw_segments:
            result.success = False
            result.error = "No transcript segments returned"
            return result

        final_language = translation_source or detected_lang or language or "en"

        segments = self._client.parse_segments(raw_segments)
        segments = self._text_cleaner.clean_segments(segments)

        plain_text = " ".join(s.text for s in segments)
        paragraph_text = self._text_cleaner.build_paragraphs(segments)
        word_count = len(plain_text.split())
        char_count = len(plain_text)
        duration = segments[-1].end if segments else 0

        available_languages = self._get_available_languages(video_id)

        return TranscriptResult(
            success=True,
            video_id=video_id,
            source=TranscriptSource.MANUAL,
            provider=TranscriptProviderName.YOUTUBE_MANUAL,
            language=final_language,
            segments=segments,
            plain_text=plain_text,
            paragraph_text=paragraph_text,
            word_count=word_count,
            character_count=char_count,
            estimated_read_time=estimate_read_time(word_count),
            duration_seconds=duration,
            available_languages=available_languages,
            translation_source=translation_source,
        )

    def supports_language(self, language: str | None) -> bool:
        return True  # YouTube captions are available in many languages

    def _get_available_languages(self, video_id: str) -> list[dict[str, Any]]:
        if not self._client:
            return []
        try:
            available = self._client.list_all_transcripts(video_id)
            return [
                {
                    "language": t["language"],
                    "language_code": t["language_code"],
                    "is_generated": t["is_generated"],
                    "is_translatable": t["is_translatable"],
                }
                for t in available
            ]
        except Exception:
            return []
