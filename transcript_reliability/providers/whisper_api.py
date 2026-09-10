"""Whisper API Provider — Priority 3.

Uses OpenAI's Whisper API for speech-to-text transcription.
Requires: OPENAI_API_KEY environment variable.
Audio is downloaded via yt-dlp, sent to OpenAI for transcription.
"""

from __future__ import annotations

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
    from openai import OpenAI
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False


class WhisperAPIProvider(BaseTranscriptProvider):
    """Priority 3: OpenAI Whisper API transcription.

    Downloads audio from YouTube, sends to OpenAI Whisper API.
    Requires: OPENAI_API_KEY env var, yt-dlp, openai package.
    Target: <20 seconds.
    """

    _provider_id = "whisper_api"
    _name = "Whisper API (OpenAI)"
    _capabilities = [ProviderCapability.STT]
    _cost_per_minute = 0.006

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._text_cleaner = TextCleaner()
        self._client = None
        if _HAS_OPENAI and self._api_key:
            try:
                self._client = OpenAI(api_key=self._api_key)
            except Exception as exc:
                logger.warning("WhisperAPI: failed to create client: %s", exc)

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

        if self._client is None:
            result.success = False
            result.error = (
                "OpenAI Whisper API not available. "
                "Set OPENAI_API_KEY and install openai package."
            )
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
            with open(audio_path, "rb") as audio_file:
                transcript = self._client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="verbose_json",
                )
        except Exception as exc:
            if audio_path:
                self._cleanup(audio_path)
            result.success = False
            result.error = f"Whisper API transcription failed: {exc}"
            return result

        segments = []
        if hasattr(transcript, "segments") and transcript.segments:
            for seg in transcript.segments:
                segments.append(TranscriptSegment(
                    start=seg.get("start", 0) if isinstance(seg, dict) else seg.start,
                    end=seg.get("end", 0) if isinstance(seg, dict) else seg.end,
                    duration=(
                        (seg.get("end", 0) - seg.get("start", 0))
                        if isinstance(seg, dict) else seg.end - seg.start
                    ),
                    text=(seg.get("text", "") if isinstance(seg, dict) else seg.text).strip(),
                ))
        else:
            text = transcript.text if hasattr(transcript, "text") else str(transcript)
            segments.append(TranscriptSegment(
                start=0.0, end=0.0, duration=0.0, text=text.strip(),
            ))

        segments = self._text_cleaner.clean_segments(segments)
        plain_text = " ".join(s.text for s in segments)
        paragraph_text = self._text_cleaner.build_paragraphs(segments)
        word_count = len(plain_text.split())
        char_count = len(plain_text)
        duration = segments[-1].end if segments else 0
        final_language = language or transcript.language if hasattr(transcript, "language") else "en"

        if audio_path:
            self._cleanup(audio_path)

        elapsed = time.time() - start
        return TranscriptResult(
            success=True,
            video_id=video_id,
            source=TranscriptSource.WHISPER,
            provider=TranscriptProviderName.FASTER_WHISPER,
            language=final_language,
            segments=segments,
            plain_text=plain_text,
            paragraph_text=paragraph_text,
            word_count=word_count,
            character_count=char_count,
            estimated_read_time=estimate_read_time(word_count),
            duration_seconds=duration,
        )

    def _download_audio(self, video_id: str) -> str:
        tmp_dir = tempfile.mkdtemp(prefix="whisper_api_")
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
