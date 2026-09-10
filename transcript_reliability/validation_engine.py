"""Validation Engine — 12-point transcript validation pipeline.

Validates every transcript against 12 quality checks before accepting it.
Rejects invalid transcripts with detailed failure reports.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from models.transcript import TranscriptResult, TranscriptSegment
from transcript_reliability.config import TranscriptReliabilityConfig
from transcript_reliability.models import ValidationReport, ValidationResult

logger = logging.getLogger(__name__)


class ValidationEngine:
    """12-point transcript validation pipeline.

    Each check produces a score (0.0-1.0). The overall score is the average
    of all checks. Transcripts below the threshold are rejected.
    """

    def __init__(self, config: TranscriptReliabilityConfig | None = None) -> None:
        self._config = config or TranscriptReliabilityConfig()

    def validate(self, transcript: TranscriptResult) -> ValidationReport:
        """Run all validation checks against a transcript.

        Args:
            transcript: The transcript to validate.

        Returns:
            ``ValidationReport`` with overall score and per-check results.
        """
        checks = [
            self._check_empty_transcript(transcript),
            self._check_minimum_length(transcript),
            self._check_broken_encoding(transcript),
            self._check_timestamp_order(transcript),
            self._check_repeated_blocks(transcript),
            self._check_missing_segments(transcript),
            self._check_invalid_characters(transcript),
            self._check_language_consistency(transcript),
            self._check_provider_integrity(transcript),
            self._check_timestamp_coverage(transcript),
            self._check_minimum_segments(transcript),
            self._check_text_segment_ratio(transcript),
        ]

        scores = [c.score for c in checks]
        overall = sum(scores) / max(len(scores), 1)
        failed = [c.check_name for c in checks if not c.passed]
        errors = [c.detail for c in checks if not c.passed]

        report = ValidationReport(
            overall_score=round(overall, 4),
            passed=overall >= self._config.validation_overall_threshold,
            checks=checks,
            failed_checks=failed,
            errors=errors,
        )

        if not report.passed:
            logger.warning(
                "Validation FAILED (score=%.2f, threshold=%.2f): %s",
                overall, self._config.validation_overall_threshold,
                ", ".join(failed),
            )

        return report

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_empty_transcript(self, transcript: TranscriptResult) -> ValidationResult:
        """Check 1: Transcript must have non-empty plain_text."""
        if not transcript.plain_text or not transcript.plain_text.strip():
            return ValidationResult(
                check_name="empty_transcript",
                passed=False,
                score=0.0,
                detail="Transcript plain_text is empty or whitespace-only",
            )
        return ValidationResult(
            check_name="empty_transcript",
            passed=True,
            score=1.0,
            detail=f"Text length: {len(transcript.plain_text)} chars",
        )

    def _check_minimum_length(self, transcript: TranscriptResult) -> ValidationResult:
        """Check 2: Word count must meet minimum threshold."""
        min_words = self._config.validation_min_word_count
        if transcript.word_count < min_words:
            return ValidationResult(
                check_name="minimum_length",
                passed=False,
                score=transcript.word_count / max(min_words, 1),
                detail=f"Word count ({transcript.word_count}) below minimum ({min_words})",
            )
        score = min(1.0, transcript.word_count / (min_words * 3))
        return ValidationResult(
            check_name="minimum_length",
            passed=True,
            score=round(score, 4),
            detail=f"Word count: {transcript.word_count}",
        )

    def _check_broken_encoding(self, transcript: TranscriptResult) -> ValidationResult:
        """Check 3: No broken or replacement characters."""
        text = transcript.plain_text
        replacement_chars = len(re.findall(r"[\ufffd\ufffe\uffff]", text))
        if replacement_chars > 0:
            return ValidationResult(
                check_name="broken_encoding",
                passed=False,
                score=max(0, 1.0 - (replacement_chars / max(len(text), 1)) * 10),
                detail=f"Found {replacement_chars} replacement characters",
            )
        return ValidationResult(
            check_name="broken_encoding",
            passed=True,
            score=1.0,
            detail="No encoding issues detected",
        )

    def _check_timestamp_order(self, transcript: TranscriptResult) -> ValidationResult:
        """Check 4: Timestamps must be monotonically increasing."""
        segments = transcript.segments
        if not segments:
            return ValidationResult(
                check_name="timestamp_order",
                passed=False,
                score=0.0,
                detail="No segments to check timestamp order",
            )

        out_of_order = 0
        for i in range(1, len(segments)):
            if segments[i].start < segments[i - 1].start:
                out_of_order += 1

        if out_of_order > 0:
            score = max(0, 1.0 - (out_of_order / len(segments)) * 5)
            return ValidationResult(
                check_name="timestamp_order",
                passed=score >= 0.5,
                score=round(score, 4),
                detail=f"{out_of_order}/{len(segments)} segments out of order",
            )
        return ValidationResult(
            check_name="timestamp_order",
            passed=True,
            score=1.0,
            detail=f"All {len(segments)} segments in order",
        )

    def _check_repeated_blocks(self, transcript: TranscriptResult) -> ValidationResult:
        """Check 5: No repeated blocks (>80% identical adjacent segments)."""
        segments = transcript.segments
        if len(segments) < 2:
            return ValidationResult(
                check_name="repeated_blocks",
                passed=True,
                score=1.0,
                detail="Too few segments to check repetition",
            )

        repeats = 0
        for i in range(1, len(segments)):
            prev = segments[i - 1].text.strip().lower()
            curr = segments[i].text.strip().lower()
            if prev and curr and self._similarity(prev, curr) > 0.8:
                repeats += 1

        if repeats > len(segments) * 0.1:  # >10% are repeats
            score = max(0, 1.0 - (repeats / len(segments)) * 3)
            return ValidationResult(
                check_name="repeated_blocks",
                passed=False,
                score=round(score, 4),
                detail=f"{repeats}/{len(segments)} segments are near-duplicates",
            )
        return ValidationResult(
            check_name="repeated_blocks",
            passed=True,
            score=1.0,
            detail=f"No repeated blocks detected",
        )

    def _check_missing_segments(self, transcript: TranscriptResult) -> ValidationResult:
        """Check 6: No gaps > max_gap_seconds between segments."""
        segments = transcript.segments
        if len(segments) < 2:
            return ValidationResult(
                check_name="missing_segments",
                passed=True,
                score=1.0,
                detail="Too few segments to check gaps",
            )

        max_gap = self._config.validation_max_gap_seconds
        large_gaps = 0
        for i in range(1, len(segments)):
            gap = segments[i].start - segments[i - 1].end
            if gap > max_gap:
                large_gaps += 1

        score = max(0, 1.0 - (large_gaps / len(segments)) * 5)
        return ValidationResult(
            check_name="missing_segments",
            passed=score >= 0.5,
            score=round(score, 4),
            detail=f"{large_gaps} gaps > {max_gap}s in {len(segments)} segments",
        )

    def _check_invalid_characters(self, transcript: TranscriptResult) -> ValidationResult:
        """Check 7: No invalid/control characters in text."""
        text = transcript.plain_text
        control_chars = len(re.findall(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", text))
        if control_chars > 0:
            score = max(0, 1.0 - (control_chars / max(len(text), 1)) * 20)
            return ValidationResult(
                check_name="invalid_characters",
                passed=control_chars < 5,
                score=round(score, 4),
                detail=f"Found {control_chars} control characters",
            )
        return ValidationResult(
            check_name="invalid_characters",
            passed=True,
            score=1.0,
            detail="No invalid characters detected",
        )

    def _check_language_consistency(self, transcript: TranscriptResult) -> ValidationResult:
        """Check 8: Language should be consistent across segments."""
        segments = transcript.segments
        if len(segments) < 3:
            return ValidationResult(
                check_name="language_consistency",
                passed=True,
                score=1.0,
                detail="Too few segments to check language consistency",
            )

        # Simple check: all segments should have text in roughly the same language
        # by checking character range distribution
        latin_counts = []
        for seg in segments[:50]:  # Sample first 50 segments
            text = seg.text
            if text:
                latin = sum(1 for c in text if "A" <= c <= "Z" or "a" <= c <= "z")
                latin_counts.append(latin / max(len(text), 1))

        if not latin_counts:
            return ValidationResult(
                check_name="language_consistency",
                passed=True,
                score=1.0,
                detail="No text to check",
            )

        mean = sum(latin_counts) / len(latin_counts)
        variance = sum((x - mean) ** 2 for x in latin_counts) / len(latin_counts)
        consistency = max(0, 1.0 - variance * 5)

        passed = consistency >= self._config.validation_language_consistency_threshold
        return ValidationResult(
            check_name="language_consistency",
            passed=passed,
            score=round(consistency, 4),
            detail=f"Language consistency score: {consistency:.2f}",
        )

    def _check_provider_integrity(self, transcript: TranscriptResult) -> ValidationResult:
        """Check 9: Provider must not claim success with empty data."""
        if transcript.success and not transcript.segments and not transcript.plain_text:
            return ValidationResult(
                check_name="provider_integrity",
                passed=False,
                score=0.0,
                detail="Provider claims success but returned no data",
            )
        return ValidationResult(
            check_name="provider_integrity",
            passed=True,
            score=1.0,
            detail=f"Provider {transcript.provider.value} returned valid data",
        )

    def _check_timestamp_coverage(self, transcript: TranscriptResult) -> ValidationResult:
        """Check 10: Timestamp coverage should be >= coverage_ratio of video."""
        segments = transcript.segments
        if not segments:
            return ValidationResult(
                check_name="timestamp_coverage",
                passed=False,
                score=0.0,
                detail="No segments to calculate coverage",
            )

        last_end = segments[-1].end if segments else 0
        video_duration = transcript.duration_seconds or last_end
        if video_duration <= 0:
            return ValidationResult(
                check_name="timestamp_coverage",
                passed=True,
                score=0.5,
                detail="Unknown video duration, cannot calculate coverage",
            )

        coverage = last_end / video_duration
        min_coverage = self._config.validation_min_coverage_ratio
        return ValidationResult(
            check_name="timestamp_coverage",
            passed=coverage >= min_coverage,
            score=round(min(1.0, coverage), 4),
            detail=f"Timestamp coverage: {coverage:.1%} (last={last_end:.1f}s, video={video_duration:.1f}s)",
        )

    def _check_minimum_segments(self, transcript: TranscriptResult) -> ValidationResult:
        """Check 11: Must have minimum number of segments."""
        min_segs = self._config.validation_min_segments
        seg_count = len(transcript.segments)
        if seg_count < min_segs:
            return ValidationResult(
                check_name="minimum_segments",
                passed=False,
                score=seg_count / max(min_segs, 1),
                detail=f"Only {seg_count} segments, minimum is {min_segs}",
            )
        return ValidationResult(
            check_name="minimum_segments",
            passed=True,
            score=1.0,
            detail=f"{seg_count} segments",
        )

    def _check_text_segment_ratio(self, transcript: TranscriptResult) -> ValidationResult:
        """Check 12: Average words per segment must be >= 2."""
        segments = transcript.segments
        if not segments:
            return ValidationResult(
                check_name="text_segment_ratio",
                passed=False,
                score=0.0,
                detail="No segments to calculate ratio",
            )
        avg_words = transcript.word_count / len(segments)
        if avg_words < 2.0:
            return ValidationResult(
                check_name="text_segment_ratio",
                passed=False,
                score=round(avg_words / 2.0, 4),
                detail=f"Average {avg_words:.1f} words per segment (minimum 2.0)",
            )
        return ValidationResult(
            check_name="text_segment_ratio",
            passed=True,
            score=min(1.0, avg_words / 10.0),
            detail=f"Average {avg_words:.1f} words per segment",
        )

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """Simple character overlap similarity."""
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        # Levenshtein-like character overlap
        set_a, set_b = set(a), set(b)
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / max(union, 1)
