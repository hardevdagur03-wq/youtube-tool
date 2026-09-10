"""Deepgram Provider — Priority 5.

Uses Deepgram's pre-recorded audio transcription API.
Requires: DEEPGRAM_API_KEY environment variable.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from typing import Any

from models.transcript import (
    TranscriptResult,
    TranscriptSource,
    TranscriptProviderName,
    TranscriptSegment,
    WhisperProcessingInfo,
)
from transcript_reliability.constants import ProviderCapability
from transcript_reliability.providers.base import BaseTranscriptProvider
from exceptions.transcript_errors import AudioDownloadError, TranscriptionError
from utils.text_cleaner import TextCleaner
from utils.read_time import estimate_read_time

logger = logging.getLogger(__name__)

try:
    import yt_dlp
    _HAS_YT_DLP = True
except ImportError:
    _HAS_YT_DLP = False

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False


class DeepgramProvider(BaseTranscriptProvider):
    """Priority 5: Deepgram pre-recorded audio transcription.

    Downloads audio from YouTube, sends to Deepgram API.
    Requires: DEEPGRAM_API_KEY env var, yt-dlp, httpx.
    Target: <25 seconds.
    """

    _provider_id = "deepgram"
    _name = "Deepgram"
    _capabilities = [ProviderCapability.STT, ProviderCapability.ASYNC]
    _cost_per_minute = 0.0059

    _DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("DEEPGRAM_API_KEY", "")
        self._text_cleaner = TextCleaner()

    def get_transcript(
        self, video_id: str, language: str | None = None, **options: Any
    ) -> TranscriptResult:
        result = TranscriptResult(
            video_id=video_id,
            source=TranscriptSource.WHISPER,
            provider=TranscriptProviderName.FASTER_WHISPER,
        )

        if not _HAS_YT_DLP:
            result.success = False
            result.error = "yt-dlp is required. Install with: pip install yt-dlp"
            return result

        if not self._api_key:
            result.success = False
            result.error = "Deepgram API key not configured. Set DEEPGRAM_API_KEY."
            return result

        audio_path = None
        start = time.time()

        try:
            audio_path = self._download_audio(video_id)
        except Exception as exc:
            result.success = False
            result.error = f"Audio download failed: {exc}"
            return result

        try:
            segments, detected_lang = self._transcribe(audio_path, language)
        except Exception as exc:
            if audio_path:
                self._cleanup(audio_path)
            result.success = False
            result.error = f"Deepgram transcription failed: {exc}"
            return result

        segments = self._text_cleaner.clean_segments(segments)
        plain_text = " ".join(s.text for s in segments)
        paragraph_text = self._text_cleaner.build_paragraphs(segments)
        word_count = len(plain_text.split())
        char_count = len(plain_text)
        duration = segments[-1].end if segments else 0

        if audio_path:
            self._cleanup(audio_path)

        return TranscriptResult(
            success=True,
            video_id=video_id,
            source=TranscriptSource.WHISPER,
            provider=TranscriptProviderName.FASTER_WHISPER,
            language=detected_lang or language or "en",
            segments=segments,
            plain_text=plain_text,
            paragraph_text=paragraph_text,
            word_count=word_count,
            character_count=char_count,
            estimated_read_time=estimate_read_time(word_count),
            duration_seconds=duration,
        )

    def _transcribe(
        self, audio_path: str, language: str | None = None,
    ) -> tuple[list[TranscriptSegment], str]:
        """Send audio to Deepgram API and parse response."""
        if not _HAS_HTTPX:
            raise TranscriptionError("httpx is required. Install with: pip install httpx")

        with open(audio_path, "rb") as f:
            audio_data = f.read()

        params = {
            "model": "nova-2",
            "punctuate": "true",
            "utterances": "true",
            "diarize": "false",
        }
        if language:
            params["language"] = language

        headers = {
            "Authorization": f"Token {self._api_key}",
            "Content-Type": "audio/*",
        }

        try:
            response = httpx.post(
                self._DEEPGRAM_URL,
                headers=headers,
                params=params,
                content=audio_data,
                timeout=120,
            )
            response.raise_for_status()
        except Exception as exc:
            raise TranscriptionError(f"Deepgram API request failed: {exc}")

        data = response.json()
        results = data.get("results", {})
        channels = results.get("channels", [])
        if not channels:
            raise TranscriptionError("No transcription channels in Deepgram response")

        alternatives = channels[0].get("alternatives", [])
        if not alternatives:
            raise TranscriptionError("No transcription alternatives in Deepgram response")

        alt = alternatives[0]
        detected_lang = alt.get("language", language or "en")
        words = alt.get("words", [])

        segments = []
        current_start = 0.0
        current_text = []

        for word in words:
            word_text = word.get("word", "")
            word_start = word.get("start", 0)
            word_end = word.get("end", 0)

            if not current_text:
                current_start = word_start
            current_text.append(word_text)

            # Create segment every ~20 words or on pauses > 0.5s
            if len(current_text) >= 20 or (word_end - current_start > 5.0):
                segments.append(TranscriptSegment(
                    start=current_start,
                    end=word_end,
                    duration=round(word_end - current_start, 2),
                    text=" ".join(current_text),
                ))
                current_text = []

        if current_text:
            segments.append(TranscriptSegment(
                start=current_start,
                end=words[-1].get("end", 0) if words else 0,
                duration=round(words[-1].get("end", 0) - current_start, 2) if words else 0,
                text=" ".join(current_text),
            ))

        return segments, detected_lang

    def _download_audio(self, video_id: str) -> str:
        tmp_dir = tempfile.mkdtemp(prefix="deepgram_")
        output_template = os.path.join(tmp_dir, f"{video_id}.%(ext)s")
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
            }],
            "quiet": True,
            "no_warnings": True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(
                    f"https://www.youtube.com/watch?v={video_id}",
                    download=True,
                )
        except Exception as exc:
            raise AudioDownloadError(f"yt-dlp download failed: {exc}")

        mp3_path = os.path.join(tmp_dir, f"{video_id}.mp3")
        if not os.path.isfile(mp3_path):
            for ext in (".m4a", ".wav", ".webm", ".opus"):
                candidate = os.path.join(tmp_dir, f"{video_id}{ext}")
                if os.path.isfile(candidate):
                    mp3_path = candidate
                    break
            else:
                raise AudioDownloadError(f"Audio file not found for {video_id}")
        return mp3_path

    @staticmethod
    def _cleanup(path: str) -> None:
        try:
            if os.path.isfile(path):
                os.unlink(path)
                parent = os.path.dirname(path)
                if os.path.isdir(parent):
                    try:
                        os.rmdir(parent)
                    except OSError:
                        pass
        except OSError as exc:
            logger.warning("Cleanup: %s", exc)
