"""Transcript Cleaning Engine — 10-stage AI-grade cleaning pipeline.

Transforms raw transcript text into AI-ready content through
a configurable pipeline of normalizers and cleaners.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Callable

from models.transcript import TranscriptResult, TranscriptSegment

logger = logging.getLogger(__name__)


class CleaningEngine:
    """Multi-stage transcript cleaning pipeline.

    Each stage is independently configurable and can be toggled.
    The pipeline runs cleaners in order, producing AI-ready output.
    """

    def __init__(self) -> None:
        self._stages: list[tuple[str, Callable[[str], str]]] = [
            ("unicode_normalizer", self._normalize_unicode),
            ("whitespace_normalizer", self._normalize_whitespace),
            ("punctuation_normalizer", self._normalize_punctuation),
            ("number_normalizer", self._normalize_numbers),
            ("special_char_normalizer", self._normalize_special_chars),
            ("emoji_remover", self._remove_emoji),
            ("broken_formatting_fixer", self._fix_broken_formatting),
            ("speaker_label_normalizer", self._normalize_speaker_labels),
            ("sentence_boundary_fixer", self._fix_sentence_boundaries),
            ("ai_ready_formatter", self._format_for_ai),
        ]
        self._enabled_stages: set[str] = {name for name, _ in self._stages}

    def disable_stage(self, stage_name: str) -> None:
        """Disable a specific cleaning stage."""
        self._enabled_stages.discard(stage_name)

    def enable_stage(self, stage_name: str) -> None:
        """Enable a specific cleaning stage."""
        self._enabled_stages.add(stage_name)

    def clean(self, transcript: TranscriptResult) -> TranscriptResult:
        """Run the full cleaning pipeline on a transcript.

        Args:
            transcript: Transcript to clean.

        Returns:
            New TranscriptResult with cleaned text and segments.
        """
        if not transcript.success or not transcript.plain_text:
            return transcript

        # Clean the full plain text
        cleaned_text = transcript.plain_text
        for name, cleaner in self._stages:
            if name in self._enabled_stages:
                try:
                    cleaned_text = cleaner(cleaned_text)
                except Exception as exc:
                    logger.warning("Cleaning stage '%s' failed: %s", name, exc)

        # Clean individual segments
        cleaned_segments = []
        for seg in transcript.segments:
            cleaned_seg_text = seg.text
            for name, cleaner in self._stages:
                if name in self._enabled_stages:
                    try:
                        cleaned_seg_text = cleaner(cleaned_seg_text)
                    except Exception:
                        pass
            cleaned_segments.append(TranscriptSegment(
                start=seg.start,
                end=seg.end,
                duration=seg.duration,
                text=cleaned_seg_text,
            ))

        # Recalculate word count
        word_count = len(cleaned_text.split())
        char_count = len(cleaned_text)

        transcript.plain_text = cleaned_text
        transcript.segments = cleaned_segments
        transcript.word_count = word_count
        transcript.character_count = char_count

        return transcript

    # ------------------------------------------------------------------
    # Cleaning stages
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_unicode(text: str) -> str:
        """Stage 1: Normalize Unicode to NFC form, remove zero-width chars."""
        text = unicodedata.normalize("NFC", text)
        text = re.sub(r"[\u200b\u200c\u200d\u200e\u200f\u2060\u2061\u2062\u2063\u2064]", "", text)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        return text

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Stage 2: Normalize whitespace — tabs to spaces, collapse multiple spaces."""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\t", " ")
        text = re.sub(r" {2,}", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _normalize_punctuation(text: str) -> str:
        """Stage 3: Normalize punctuation — smart quotes, dashes, ellipsis."""
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u201e", '"').replace("\u201f", '"')
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        text = text.replace("\u201a", "'").replace("\u201b", "'")
        text = text.replace("\u2013", "-").replace("\u2014", " — ")
        text = re.sub(r"\.{4,}", "...", text)
        text = re.sub(r"!{3,}", "!!", text)
        text = re.sub(r"\?{3,}", "??", text)
        text = re.sub(r"\s+\.", ".", text)
        text = re.sub(r"\s+,", ",", text)
        text = re.sub(r"\s+!", "!", text)
        text = re.sub(r"\s+\?", "?", text)
        return text

    @staticmethod
    def _normalize_numbers(text: str) -> str:
        """Stage 4: Normalize number formats — consistent spacing/formatting."""
        text = re.sub(r"(\d)\s+(\d{3})", r"\1\2", text)  # Remove spaces in numbers
        text = re.sub(r"(\d)\.(\d{3})", r"\1\2", text)    # Fix thousand separators
        return text

    @staticmethod
    def _normalize_special_chars(text: str) -> str:
        """Stage 5: Normalize special characters — copyright, registered, etc."""
        text = text.replace("\u00a9", "(c)").replace("\u00ae", "(r)")
        text = text.replace("\u2122", "(tm)")
        text = re.sub(r"[\u2020\u2021\u2030]", "", text)  # Dagger, double dagger, per mille
        return text

    @staticmethod
    def _remove_emoji(text: str) -> str:
        """Stage 6: Remove emoji characters or replace them with text."""
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F]"   # Emoticons
            "|[\U0001F300-\U0001F5FF]"  # Misc Symbols and Pictographs
            "|[\U0001F680-\U0001F6FF]"  # Transport and Map
            "|[\U0001F1E0-\U0001F1FF]"  # Flags
            "|[\U00002702-\U000027B0]"  # Dingbats
            "|[\U000024C2-\U0001F251]"  # Enclosed
            "|[\U0000200D]"             # Zero width joiner
            "|[\U0000FE00-\U0000FE0F]"  # Variation selectors
            "|[\U000020E3]"             # Combining enclosing keycap
            "|[\U00002600-\U000026FF]"  # Miscellaneous symbols
            "|[\U00002934-\U0000293F]"  # Misc arrows
            "|[\U00002B05-\U00002B07]"  # Arrows
            "|[\U00003030-\U0000303F]"  # CJK Symbols
        )
        return emoji_pattern.sub("", text)

    @staticmethod
    def _fix_broken_formatting(text: str) -> str:
        """Stage 7: Fix broken formatting — line breaks, indentation."""
        text = re.sub(r"\n+", "\n", text)
        text = re.sub(r"^[ \t]+", "", text, flags=re.MULTILINE)
        return text

    @staticmethod
    def _normalize_speaker_labels(text: str) -> str:
        """Stage 8: Normalize speaker labels."""
        text = re.sub(r"\b(Speaker)\s*(\d+):", r"**Speaker \2:**", text)
        text = re.sub(r"\b(SPEAKER)\s*(\d+):", r"**Speaker \2:**", text)
        text = re.sub(r"\bspeaker\s*(\d+):", r"**Speaker \1:**", text)
        text = re.sub(r"\b(Host|Hostess):", r"**Host:**", text)
        text = re.sub(r"\b(Guest|Guests?):", r"**Guest:**", text)
        text = re.sub(r"\b(Moderator):", r"**Moderator:**", text)
        text = re.sub(r"\b(Interviewer):", r"**Interviewer:**", text)
        text = re.sub(r"\b(Interviewee):", r"**Interviewee:**", text)
        return text

    @staticmethod
    def _fix_sentence_boundaries(text: str) -> str:
        """Stage 9: Ensure proper spacing after sentence endings."""
        text = re.sub(r"\.([A-Z])", r". \1", text)
        text = re.sub(r"!([A-Z])", r"! \1", text)
        text = re.sub(r"\?([A-Z])", r"? \1", text)
        return text

    @staticmethod
    def _format_for_ai(text: str) -> str:
        """Stage 10: Final formatting pass for AI consumption."""
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n{2,}", "\n\n", text)
        return text.strip()
