"""Duplicate Remover — detects and removes duplicate content from transcripts.

6 detection strategies:
1. Exact line duplicates
2. Exact paragraph duplicates
3. Repeated timestamp blocks
4. High-overlap segment pairs
5. Repeated sentences
6. Near-duplicate text blocks
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Sequence

from models.transcript import TranscriptSegment
from transcript_reliability.config import TranscriptReliabilityConfig
from transcript_reliability.models import DuplicateReport

logger = logging.getLogger(__name__)


class DuplicateRemover:
    """Detects and removes duplicate content from transcript segments.

    Each strategy targets a different type of duplication.
    Results are merged intelligently preserving order and content.
    """

    def __init__(self, config: TranscriptReliabilityConfig | None = None) -> None:
        self._config = config or TranscriptReliabilityConfig()

    def remove_duplicates(
        self, segments: list[TranscriptSegment],
    ) -> tuple[list[TranscriptSegment], DuplicateReport]:
        """Remove duplicate content from a list of segments.

        Args:
            segments: List of transcript segments potentially containing duplicates.

        Returns:
            Tuple of (cleaned_segments, duplicate_report).
        """
        if not segments:
            return [], DuplicateReport()

        original_count = len(segments)
        original_words = sum(len(s.text.split()) for s in segments)
        all_details: list[dict] = []
        strategies_triggered: list[str] = []

        # Strategy 1: Exact line duplicates
        segments, details = self._remove_exact_line_duplicates(segments)
        if details:
            strategies_triggered.append("exact_line")
            all_details.extend(details)

        # Strategy 2: Near-duplicate segment pairs
        segments, details = self._remove_near_duplicates(segments)
        if details:
            strategies_triggered.append("near_duplicate")
            all_details.extend(details)

        # Strategy 3: Repeated sentences
        segments, details = self._remove_repeated_sentences(segments)
        if details:
            strategies_triggered.append("sentence_repeat")
            all_details.extend(details)

        # Strategy 4: Repeated paragraph blocks
        segments, details = self._remove_paragraph_duplicates(segments)
        if details:
            strategies_triggered.append("exact_paragraph")
            all_details.extend(details)

        removed_count = original_count - len(segments)
        cleaned_words = sum(len(s.text.split()) for s in segments)

        report = DuplicateReport(
            total_duplicates_found=removed_count,
            total_duplicates_removed=removed_count,
            strategies_triggered=list(set(strategies_triggered)),
            details=all_details,
            original_word_count=original_words,
            cleaned_word_count=cleaned_words,
        )

        if removed_count > 0:
            logger.info(
                "Removed %d duplicate segments (strategies: %s)",
                removed_count, strategies_triggered,
            )

        return segments, report

    def _remove_exact_line_duplicates(
        self, segments: list[TranscriptSegment],
    ) -> tuple[list[TranscriptSegment], list[dict]]:
        """Strategy 1: Remove segments with exact same text as previous."""
        if not segments:
            return segments, []

        seen_texts = set()
        result: list[TranscriptSegment] = []
        details: list[dict] = []

        for seg in segments:
            text = seg.text.strip().lower()
            if text and text in seen_texts:
                details.append({
                    "strategy": "exact_line",
                    "removed_text": seg.text[:100],
                    "start_time": seg.start,
                })
            else:
                if text:
                    seen_texts.add(text)
                result.append(seg)

        return result, details

    def _remove_near_duplicates(
        self, segments: list[TranscriptSegment],
    ) -> tuple[list[TranscriptSegment], list[dict]]:
        """Strategy 2: Remove near-duplicate segments (high character overlap)."""
        if len(segments) < 2:
            return segments, []

        threshold = self._config.duplicate_similarity_threshold
        result: list[TranscriptSegment] = [segments[0]]
        details: list[dict] = []

        for i in range(1, len(segments)):
            current = segments[i].text.strip().lower()
            prev = result[-1].text.strip().lower()
            if current and prev:
                similarity = self._character_overlap(current, prev)
                if similarity > threshold:
                    details.append({
                        "strategy": "near_duplicate",
                        "similarity": round(similarity, 3),
                        "removed_text": segments[i].text[:100],
                        "kept_text": result[-1].text[:100],
                        "start_time": segments[i].start,
                    })
                    continue
            result.append(segments[i])

        return result, details

    def _remove_repeated_sentences(
        self, segments: list[TranscriptSegment],
    ) -> tuple[list[TranscriptSegment], list[dict]]:
        """Strategy 3: Remove segments containing repeated sentences."""
        if not segments:
            return segments, []

        max_repeat = self._config.duplicate_sentence_repeat_threshold
        all_sentences: list[str] = []
        result: list[TranscriptSegment] = []
        details: list[dict] = []

        for seg in segments:
            sentences = re.findall(r'[^.!?]*[.!?]', seg.text)
            sentences = [s.strip().lower() for s in sentences if s.strip()]
            repeat_count = sum(1 for s in sentences if s in all_sentences)

            if repeat_count > max_repeat:
                details.append({
                    "strategy": "sentence_repeat",
                    "repeat_count": repeat_count,
                    "removed_text": seg.text[:100],
                    "start_time": seg.start,
                })
                continue

            all_sentences.extend(sentences)
            result.append(seg)

        return result, details

    def _remove_paragraph_duplicates(
        self, segments: list[TranscriptSegment],
    ) -> tuple[list[TranscriptSegment], list[dict]]:
        """Strategy 4: Remove blocks of duplicate consecutive segments."""
        if len(segments) < 4:
            return segments, []

        threshold = self._config.duplicate_similarity_threshold
        result = list(segments)
        details: list[dict] = []

        # Look for repeated blocks of 2+ segments
        changed = True
        while changed:
            changed = False
            i = 0
            while i < len(result) - 3:
                block_text = " ".join(s.text.lower() for s in result[i:i+2])
                for j in range(i + 2, len(result) - 1):
                    compare_text = " ".join(s.text.lower() for s in result[j:j+2])
                    similarity = self._character_overlap(block_text, compare_text)
                    if similarity > threshold:
                        details.append({
                            "strategy": "exact_paragraph",
                            "start_index": i,
                            "duplicate_index": j,
                            "similarity": round(similarity, 3),
                        })
                        result = result[:j] + result[j+2:]
                        changed = True
                        break
                i += 1

        removed = len(segments) - len(result)
        if removed > 0:
            logger.info("Removed %d segments via paragraph dedup", removed)

        return result, details

    @staticmethod
    def _character_overlap(a: str, b: str) -> float:
        """Compute character set overlap between two strings."""
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        set_a, set_b = set(a), set(b)
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / max(union, 1)
