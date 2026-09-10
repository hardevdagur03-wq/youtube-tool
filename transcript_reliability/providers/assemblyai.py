"""AssemblyAI Provider — Priority 6.

Uses AssemblyAI's async audio transcription API.
Requires: ASSEMBLYAI_API_KEY environment variable.
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


class AssemblyAIProvider(BaseTranscriptProvider):
    """Priority 6: AssemblyAI async transcription.

    Downloads audio from YouTube, submits to AssemblyAI, polls for completion.
    Requires: ASSEMBLYAI_API_KEY env var, yt-dlp, httpx.
    Target: <30 seconds.
    """

    _provider_id = "assemblyai"
    _name = "AssemblyAI"
    _capabilities = [ProviderCapability.STT, ProviderCapability.ASYNC]
    _cost_per_minute = 0.015

    _BASE_URL = "https://api.assemblyai.com/v2"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("ASSEMBLYAI_API_KEY", "")
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
            result.error = "AssemblyAI API key not configured. Set ASSEMBLYAI_API_KEY."
            return result

        if not _HAS_HTTPX:
            result.success = False
            result.error = "httpx is required. Install with: pip install httpx"
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
            result.error = f"AssemblyAI transcription failed: {exc}"
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
        """Submit audio to AssemblyAI and poll for completion."""
        headers = {"authorization": self._api_key}

        # Step 1: Upload audio
        try:
            with open(audio_path, "rb") as f:
                upload_resp = httpx.post(
                    f"{self._BASE_URL}/upload",
                    headers=headers,
                    content=f,
                    timeout=120,
                )
                upload_resp.raise_for_status()
                audio_url = upload_resp.json().get("upload_url")
        except Exception as exc:
            raise TranscriptionError(f"AssemblyAI upload failed: {exc}")

        if not audio_url:
            raise TranscriptionError("No upload_url in AssemblyAI response")

        # Step 2: Submit transcription
        transcript_request = {
            "audio_url": audio_url,
            "punctuate": True,
            "format_text": True,
        }
        if language:
            transcript_request["language_code"] = language

        try:
            submit_resp = httpx.post(
                f"{self._BASE_URL}/transcript",
                headers=headers,
                json=transcript_request,
                timeout=30,
            )
            submit_resp.raise_for_status()
            transcript_id = submit_resp.json().get("id")
        except Exception as exc:
            raise TranscriptionError(f"AssemblyAI submit failed: {exc}")

        if not transcript_id:
            raise TranscriptionError("No transcript ID in AssemblyAI response")

        # Step 3: Poll for completion (async)
        max_poll_time = 120
        poll_interval = 3
        poll_start = time.time()

        while time.time() - poll_start < max_poll_time:
            try:
                poll_resp = httpx.get(
                    f"{self._BASE_URL}/transcript/{transcript_id}",
                    headers=headers,
                    timeout=30,
                )
                poll_resp.raise_for_status()
                data = poll_resp.json()
            except Exception as exc:
                raise TranscriptionError(f"AssemblyAI poll failed: {exc}")

            status = data.get("status")
            if status == "completed":
                break
            elif status == "error":
                error_msg = data.get("error", "Unknown error")
                raise TranscriptionError(f"AssemblyAI transcription error: {error_msg}")
            time.sleep(poll_interval)
        else:
            raise TranscriptionError("AssemblyAI transcription timed out")

        # Step 4: Parse response
        detected_lang = data.get("language_code", language or "en")
        words = data.get("words", [])
        text = data.get("text", "")

        segments = []
        current_start = 0.0
        current_text = []

        for word_data in words:
            word_text = word_data.get("text", "")
            word_start = word_data.get("start", 0) / 1000.0  # ms to seconds
            word_end = word_data.get("end", 0) / 1000.0

            if not current_text:
                current_start = word_start
            current_text.append(word_text)

            if len(current_text) >= 20:
                segments.append(TranscriptSegment(
                    start=current_start,
                    end=word_end,
                    duration=round(word_end - current_start, 2),
                    text=" ".join(current_text),
                ))
                current_text = []

        if current_text and words:
            segments.append(TranscriptSegment(
                start=current_start,
                end=words[-1].get("end", 0) / 1000.0,
                duration=round((words[-1].get("end", 0) / 1000.0) - current_start, 2),
                text=" ".join(current_text),
            ))

        if not segments and text:
            segments.append(TranscriptSegment(
                start=0.0, end=0.0, duration=0.0, text=text,
            ))

        return segments, detected_lang

    def _download_audio(self, video_id: str) -> str:
        tmp_dir = tempfile.mkdtemp(prefix="assemblyai_")
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
