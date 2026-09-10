"""Whisper Local Provider — Priority 4.

Uses faster-whisper (local CTranslate2-optimized Whisper) for speech-to-text.
Downloads audio via yt-dlp, transcribes locally.
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
    from clients.whisper_client import FasterWhisperClient
    _HAS_WHISPER = True
except ImportError:
    _HAS_WHISPER = False


class WhisperLocalProvider(BaseTranscriptProvider):
    """Priority 4: Local Whisper transcription via faster-whisper.

    Downloads audio from YouTube and transcribes locally.
    Requires: yt-dlp, faster-whisper, ffmpeg.
    """

    _provider_id = "whisper_local"
    _name = "Whisper Local"
    _capabilities = [ProviderCapability.STT]
    _cost_per_minute = 0.0

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "auto",
        keep_audio: bool = False,
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._keep_audio = keep_audio
        self._text_cleaner = TextCleaner()
        self._stt = None
        if _HAS_WHISPER:
            try:
                self._stt = FasterWhisperClient(
                    model_size=model_size,
                    device=device,
                    compute_type=compute_type,
                )
            except Exception as exc:
                logger.warning("WhisperLocal: failed to initialize STT: %s", exc)

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

        if self._stt is None:
            result.success = False
            result.error = "faster-whisper is not available. Install with: pip install faster-whisper"
            return result

        audio_path = None
        download_start = time.time()

        try:
            audio_path = self._download_audio(video_id)
            download_time = time.time() - download_start
        except Exception as exc:
            result.success = False
            result.error = f"Audio download failed: {exc}"
            return result

        try:
            stt_result = self._stt.transcribe(audio_path, language=language)
        except Exception as exc:
            if audio_path:
                self._cleanup(audio_path)
            result.success = False
            result.error = f"Whisper transcription failed: {exc}"
            return result

        segments = [
            TranscriptSegment(
                start=seg.start,
                end=seg.end,
                duration=round(seg.end - seg.start, 2),
                text=seg.text.strip(),
            )
            for seg in stt_result.segments
            if seg.text.strip()
        ]

        segments = self._text_cleaner.clean_segments(segments)
        plain_text = " ".join(s.text for s in segments)
        paragraph_text = self._text_cleaner.build_paragraphs(segments)
        word_count = len(plain_text.split())
        char_count = len(plain_text)
        duration = segments[-1].end if segments else 0
        final_language = stt_result.language or language or "en"

        if audio_path and not self._keep_audio:
            self._cleanup(audio_path)

        return TranscriptResult(
            success=True,
            video_id=video_id,
            source=TranscriptSource.WHISPER,
            provider=TranscriptProviderName.FASTER_WHISPER,
            language=final_language,
            language_confidence=stt_result.language_confidence,
            segments=segments,
            plain_text=plain_text,
            paragraph_text=paragraph_text,
            word_count=word_count,
            character_count=char_count,
            estimated_read_time=estimate_read_time(word_count),
            duration_seconds=duration,
            whisper_info=WhisperProcessingInfo(
                model_name=self._stt.model_name() if self._stt else "unknown",
                transcription_duration_seconds=stt_result.processing_time_seconds,
                audio_duration_seconds=stt_result.duration_seconds,
                language_detected=stt_result.language,
                language_confidence=stt_result.language_confidence,
            ),
        )

    def _download_audio(self, video_id: str) -> str:
        tmp_dir = tempfile.mkdtemp(prefix="whisper_")
        output_template = os.path.join(tmp_dir, f"{video_id}.%(ext)s")

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            }],
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(
                    f"https://www.youtube.com/watch?v={video_id}",
                    download=True,
                )
        except Exception as exc:
            raise AudioDownloadError(f"yt-dlp download failed: {exc}")

        wav_path = os.path.join(tmp_dir, f"{video_id}.wav")
        if not os.path.isfile(wav_path):
            for ext in (".m4a", ".mp3", ".webm", ".opus"):
                candidate = os.path.join(tmp_dir, f"{video_id}{ext}")
                if os.path.isfile(candidate):
                    wav_path = candidate
                    break
            else:
                raise AudioDownloadError(f"Audio file not found for {video_id}")

        return wav_path

    @staticmethod
    def _cleanup(path: str) -> None:
        try:
            if os.path.isfile(path):
                os.unlink(path)
                parent = os.path.dirname(path)
                if os.path.isdir(parent) and "whisper_" in os.path.basename(parent):
                    try:
                        os.rmdir(parent)
                    except OSError:
                        pass
        except OSError as exc:
            logger.warning("Cleanup warning: %s", exc)
