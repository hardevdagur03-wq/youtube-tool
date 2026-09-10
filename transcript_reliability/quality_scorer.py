"""Quality Scoring Engine — 8-dimension weighted transcript quality assessment.

Generates overall quality scores with dimension breakdowns and letter grades.
Stores quality history for trend analysis.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from models.transcript import TranscriptResult
from transcript_reliability.config import TranscriptReliabilityConfig
from transcript_reliability.constants import QualityGrade
from transcript_reliability.models import QualityDimension, QualityScore

logger = logging.getLogger(__name__)


class QualityScorer:
    """8-dimension weighted quality scoring for transcripts.

    Each dimension scores 0.0-1.0. Overall is weighted sum.
    Grade: EXCELLENT (≥0.9), GOOD (≥0.7), FAIR (≥0.5), POOR (≥0.3), REJECT (<0.3).
    """

    # Weight configuration for each dimension (must sum to 1.0)
    _DIMENSION_WEIGHTS = {
        "completeness": 0.20,
        "readability": 0.15,
        "confidence": 0.15,
        "timestamp_quality": 0.10,
        "language_score": 0.10,
        "noise_score": 0.10,
        "duplicate_score": 0.10,
        "provider_reliability": 0.10,
    }

    def __init__(self, config: TranscriptReliabilityConfig | None = None) -> None:
        self._config = config or TranscriptReliabilityConfig()
        self._history: dict[str, list[QualityScore]] = {}

    def score(self, transcript: TranscriptResult,
              provider_reliability: float = 0.5) -> QualityScore:
        """Compute a quality score for a transcript.

        Args:
            transcript: The transcript to score.
            provider_reliability: Provider's historical reliability score (0-1).

        Returns:
            ``QualityScore`` with overall, grade, and dimension breakdown.
        """
        dimensions = [
            QualityDimension(
                name="completeness",
                score=self._score_completeness(transcript),
                weight=self._DIMENSION_WEIGHTS["completeness"],
                detail=f"word_count={transcript.word_count}",
            ),
            QualityDimension(
                name="readability",
                score=self._score_readability(transcript),
                weight=self._DIMENSION_WEIGHTS["readability"],
                detail=f"avg_words_per_segment={self._avg_words_per_segment(transcript):.1f}",
            ),
            QualityDimension(
                name="confidence",
                score=self._score_confidence(transcript),
                weight=self._DIMENSION_WEIGHTS["confidence"],
                detail=f"lang_conf={transcript.language_confidence or 0}",
            ),
            QualityDimension(
                name="timestamp_quality",
                score=self._score_timestamp_quality(transcript),
                weight=self._DIMENSION_WEIGHTS["timestamp_quality"],
                detail=f"segments={len(transcript.segments)}",
            ),
            QualityDimension(
                name="language_score",
                score=self._score_language(transcript),
                weight=self._DIMENSION_WEIGHTS["language_score"],
                detail=f"lang={transcript.language}",
            ),
            QualityDimension(
                name="noise_score",
                score=self._score_noise(transcript),
                weight=self._DIMENSION_WEIGHTS["noise_score"],
                detail=f"source={transcript.source.value}",
            ),
            QualityDimension(
                name="duplicate_score",
                score=self._score_duplicates(transcript),
                weight=self._DIMENSION_WEIGHTS["duplicate_score"],
                detail="dedup_score",
            ),
            QualityDimension(
                name="provider_reliability",
                score=min(1.0, provider_reliability),
                weight=self._DIMENSION_WEIGHTS["provider_reliability"],
                detail=f"provider={transcript.provider.value}",
            ),
        ]

        overall = sum(d.score * d.weight for d in dimensions)
        grade = self._grade(overall)

        quality = QualityScore(
            overall=round(overall, 4),
            grade=grade,
            dimensions=dimensions,
            provider_reliability_score=round(provider_reliability, 4),
        )

        # Store history
        video_id = transcript.video_id
        if video_id not in self._history:
            self._history[video_id] = []
        self._history[video_id].append(quality)
        # Keep last 100 scores per video
        if len(self._history[video_id]) > 100:
            self._history[video_id] = self._history[video_id][-100:]

        logger.debug(
            "Quality score for %s: %.2f (%s)",
            transcript.video_id, overall, grade.value,
        )

        return quality

    def _score_completeness(self, transcript: TranscriptResult) -> float:
        """Dimension 1: How complete is the transcript?"""
        if not transcript.success:
            return 0.0
        # Expected words per minute of video: ~150
        expected_words = (transcript.duration_seconds or 300) / 60 * 150
        if expected_words <= 0:
            return 0.5
        ratio = min(1.0, transcript.word_count / expected_words)
        return ratio

    def _score_readability(self, transcript: TranscriptResult) -> float:
        """Dimension 2: Readability based on average words per segment."""
        avg = self._avg_words_per_segment(transcript)
        if avg < 2:
            return 0.2  # Too fragmented
        if avg < 5:
            return 0.5  # Somewhat fragmented
        if avg < 15:
            return 0.8  # Good
        if avg < 30:
            return 1.0  # Excellent
        return 0.7  # Very long segments (run-on)

    def _score_confidence(self, transcript: TranscriptResult) -> float:
        """Dimension 3: Language confidence score."""
        conf = transcript.language_confidence
        if conf is None:
            return 0.5  # Unknown = neutral
        return min(1.0, max(0.0, conf))

    def _score_timestamp_quality(self, transcript: TranscriptResult) -> float:
        """Dimension 4: Quality of timestamp coverage."""
        segments = transcript.segments
        if not segments:
            return 0.0
        duration = transcript.duration_seconds or (segments[-1].end if segments else 0)
        if duration <= 0:
            return 0.5
        segment_density = len(segments) / (duration / 30)  # Expected: ~1 per 30s
        return min(1.0, segment_density / 2.0)

    def _score_language(self, transcript: TranscriptResult) -> float:
        """Dimension 5: Language detection confidence."""
        lang = transcript.language or "en"
        # Known languages get 1.0, unknown get lower
        known_languages = {"en", "es", "fr", "de", "it", "pt", "ru", "zh",
                           "ja", "ko", "ar", "hi", "bn", "pa", "ta", "te",
                           "mr", "gu", "kn", "ml", "nl", "pl", "tr", "vi",
                           "th", "sv", "da", "fi", "no", "cs", "hu", "ro",
                           "el", "he", "id", "ms"}
        if lang in known_languages:
            return 0.9
        return 0.5

    def _score_noise(self, transcript: TranscriptResult) -> float:
        """Dimension 6: Noise level in transcript."""
        # Manual and auto captions are clean
        source = transcript.source.value if hasattr(transcript.source, 'value') else str(transcript.source)
        if source in ("manual", "auto", "youtube_manual", "youtube_auto"):
            return 0.95
        if source in ("whisper", "faster_whisper", "whisper_api"):
            return 0.80
        # STT providers have some noise
        return 0.70

    def _score_duplicates(self, transcript: TranscriptResult) -> float:
        """Dimension 7: Duplicate content penalty."""
        # If pipeline_steps has a duplicate report, use it
        pipeline = getattr(transcript, 'pipeline_steps', None) or []
        for step in pipeline:
            if isinstance(step, dict) and step.get("name") == "duplicate_removal":
                removed = step.get("detail", {}).get("removed", 0)
                if removed > 0:
                    return max(0.3, 1.0 - (removed * 0.1))
        return 1.0

    @staticmethod
    def _avg_words_per_segment(transcript: TranscriptResult) -> float:
        """Calculate average words per segment."""
        segments = transcript.segments
        if not segments:
            return 0.0
        return transcript.word_count / len(segments)

    @staticmethod
    def _grade(score: float) -> QualityGrade:
        """Convert numeric score to letter grade."""
        if score >= 0.9:
            return QualityGrade.EXCELLENT
        if score >= 0.7:
            return QualityGrade.GOOD
        if score >= 0.5:
            return QualityGrade.FAIR
        if score >= 0.3:
            return QualityGrade.POOR
        return QualityGrade.REJECT

    def get_history(self, video_id: str, limit: int = 10) -> list[QualityScore]:
        """Get quality score history for a video."""
        return self._history.get(video_id, [])[-limit:]

    def get_trend(self, video_id: str) -> str:
        """Get quality trend direction for a video."""
        history = self._history.get(video_id, [])
        if len(history) < 2:
            return "stable"
        recent = [h.overall for h in history[-5:]]
        if len(recent) < 2:
            return "stable"
        if recent[-1] > recent[0]:
            return "improving"
        if recent[-1] < recent[0]:
            return "declining"
        return "stable"
