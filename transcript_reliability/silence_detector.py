"""Silence Detector — detects unusable transcripts (silence, music, noise).

6 detection patterns:
1. Silent audio — all empty segments
2. Music only — only instrumental markers
3. Long pauses — gaps > 10s between segments
4. Empty captions — [Music], [Applause], [Silence] only
5. Placeholder captions — [inaudible], [unintelligible], [__]
6. Noise only — all segments are noise markers
"""

from __future__ import annotations

import logging
import re
from typing import Any

from models.transcript import TranscriptResult, TranscriptSegment
from transcript_reliability.config import TranscriptReliabilityConfig
from transcript_reliability.models import SilenceResult

logger = logging.getLogger(__name__)

# Patterns that indicate non-speech content
_MUSIC_PATTERNS = [
    r"\[musi[ck]\]",
    r"\(musi[ck]\)",
    r"{musi[ck]}",
    r"♪",
    r"♫",
    r"♬",
    r"🎵",
    r"🎶",
]

_EMPTY_CAPTION_PATTERNS = [
    r"\[musi[ck]\]",
    r"\(musi[ck]\)",
    r"\[applause\]",
    r"\(applause\)",
    r"\[laughter\]",
    r"\(laughter\)",
    r"\[silence\]",
    r"\(silence\)",
    r"\[noise\]",
    r"\(noise\)",
    r"\[inaudible\]",
]

_PLACEHOLDER_PATTERNS = [
    r"\[inaudible\]",
    r"\(inaudible\)",
    r"\[unintelligible\]",
    r"\(unintelligible\)",
    r"\[__\]",
    r"\[\?\]",
    r"\(__\)",
    r"\(\.\.\.\)",
    r"\[\.\.\.\]",
    r"\[foreign language\]",
    r"\(foreign language\)",
    r"\[indistinct\]",
    r"\(indistinct\)",
]

_NOISE_PATTERNS = [
    r"\[noise\]",
    r"\(noise\)",
    r"\[static\]",
    r"\(static\)",
    r"\[beep\]",
    r"\(beep\)",
    r"\[tone\]",
    r"\(tone\)",
    r"\[click\]",
    r"\(click\)",
]

# Combined pattern for quick matching
_ALL_NON_SPEECH = re.compile(
    "|".join(
        _MUSIC_PATTERNS + _EMPTY_CAPTION_PATTERNS
        + _PLACEHOLDER_PATTERNS + _NOISE_PATTERNS
    ),
    re.IGNORECASE,
)


class SilenceDetector:
    """Detects transcripts that contain only silence, music, or noise.

    Runs 6 detection patterns and returns a combined assessment.
    Unusable transcripts are rejected before they reach the AI pipeline.
    """

    def __init__(self, config: TranscriptReliabilityConfig | None = None) -> None:
        self._config = config or TranscriptReliabilityConfig()

    def detect(self, transcript: TranscriptResult) -> SilenceResult:
        """Run all silence detection patterns against a transcript.

        Args:
            transcript: The transcript to check.

        Returns:
            ``SilenceResult`` with is_silent flag and confidence.
        """
        patterns_detected: list[str] = []
        details: dict[str, Any] = {}

        patterns = [
            ("silent_audio", self._detect_silent_audio),
            ("music_only", self._detect_music_only),
            ("long_pauses", self._detect_long_pauses),
            ("empty_captions", self._detect_empty_captions),
            ("placeholder_captions", self._detect_placeholder_captions),
            ("noise_only", self._detect_noise_only),
        ]

        for name, detector in patterns:
            result = detector(transcript)
            if result["detected"]:
                patterns_detected.append(name)
            details[name] = result

        is_silent = len(patterns_detected) >= 2  # At least 2 patterns must trigger

        # Calculate confidence based on patterns detected
        confidence = 0.0
        if patterns_detected:
            confidence = min(1.0, len(patterns_detected) * 0.3)

        result = SilenceResult(
            is_silent=is_silent,
            confidence=round(confidence, 2),
            patterns_detected=patterns_detected if is_silent else [],
            details=details,
        )

        if is_silent:
            logger.warning(
                "Silence detected: %s (confidence=%.2f)",
                patterns_detected, confidence,
            )

        return result

    def _detect_silent_audio(self, transcript: TranscriptResult) -> dict[str, Any]:
        """Pattern 1: All segments have empty text."""
        segments = transcript.segments
        if not segments:
            return {"detected": True, "reason": "No segments at all", "empty_ratio": 1.0}

        empty = sum(1 for s in segments if not s.text.strip())
        ratio = empty / len(segments)
        return {
            "detected": ratio > 0.9,
            "reason": f"{empty}/{len(segments)} segments empty",
            "empty_ratio": round(ratio, 3),
        }

    def _detect_music_only(self, transcript: TranscriptResult) -> dict[str, Any]:
        """Pattern 2: All non-empty text is music markers."""
        segments = transcript.segments
        non_empty = [s for s in segments if s.text.strip()]
        if not non_empty:
            return {"detected": False, "reason": "No text to check", "music_ratio": 0.0}

        music_count = sum(
            1 for s in non_empty
            if re.search("|".join(_MUSIC_PATTERNS), s.text, re.IGNORECASE)
        )
        ratio = music_count / len(non_empty)
        return {
            "detected": ratio > 0.8,
            "reason": f"{music_count}/{len(non_empty)} segments are music markers",
            "music_ratio": round(ratio, 3),
        }

    def _detect_long_pauses(self, transcript: TranscriptResult) -> dict[str, Any]:
        """Pattern 3: Gaps between segments exceed threshold."""
        segments = transcript.segments
        if len(segments) < 2:
            return {"detected": False, "reason": "Too few segments", "max_gap": 0.0}

        max_gap = self._config.silence_max_gap_seconds
        gaps = [segments[i].start - segments[i - 1].end for i in range(1, len(segments))]
        max_gap_found = max(gaps) if gaps else 0
        large_gaps = sum(1 for g in gaps if g > max_gap)

        return {
            "detected": large_gaps > len(segments) * 0.2,  # >20% have excessive gaps
            "reason": f"Max gap: {max_gap_found:.1f}s, {large_gaps} gaps > {max_gap}s",
            "max_gap": round(max_gap_found, 1),
            "large_gap_count": large_gaps,
        }

    def _detect_empty_captions(self, transcript: TranscriptResult) -> dict[str, Any]:
        """Pattern 4: Only caption markers like [Music], [Applause]."""
        segments = transcript.segments
        if not segments:
            return {"detected": False, "reason": "No segments", "caption_ratio": 0.0}

        caption_only = sum(
            1 for s in segments
            if s.text.strip()
            and re.match("|".join(_EMPTY_CAPTION_PATTERNS), s.text.strip(), re.IGNORECASE)
        )
        ratio = caption_only / len(segments)
        return {
            "detected": ratio > 0.7,
            "reason": f"{caption_only}/{len(segments)} segments are caption markers",
            "caption_ratio": round(ratio, 3),
        }

    def _detect_placeholder_captions(self, transcript: TranscriptResult) -> dict[str, Any]:
        """Pattern 5: Placeholder text like [inaudible], [__]."""
        segments = transcript.segments
        non_empty = [s for s in segments if s.text.strip()]
        if not non_empty:
            return {"detected": False, "reason": "No text to check", "placeholder_ratio": 0.0}

        placeholder_count = sum(
            1 for s in non_empty
            if re.match("|".join(_PLACEHOLDER_PATTERNS), s.text.strip(), re.IGNORECASE)
        )
        ratio = placeholder_count / len(non_empty)
        return {
            "detected": ratio > 0.5,
            "reason": f"{placeholder_count}/{len(non_empty)} segments are placeholders",
            "placeholder_ratio": round(ratio, 3),
        }

    def _detect_noise_only(self, transcript: TranscriptResult) -> dict[str, Any]:
        """Pattern 6: All text is noise markers."""
        segments = transcript.segments
        non_empty = [s for s in segments if s.text.strip()]
        if not non_empty:
            return {"detected": False, "reason": "No text to check", "noise_ratio": 0.0}

        noise_count = sum(
            1 for s in non_empty
            if re.match("|".join(_NOISE_PATTERNS), s.text.strip(), re.IGNORECASE)
        )
        ratio = noise_count / len(non_empty)
        return {
            "detected": ratio > 0.5,
            "reason": f"{noise_count}/{len(non_empty)} segments are noise markers",
            "noise_ratio": round(ratio, 3),
        }
