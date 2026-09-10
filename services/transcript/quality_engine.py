"""Transcript quality and confidence scoring engine."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class QualityScore:
    overall: float = 0.0
    word_accuracy: float = 0.0
    sentence_accuracy: float = 0.0
    grammar_score: float = 0.0
    completeness: float = 0.0
    timestamp_accuracy: float = 0.0
    confidence: float = 0.0
    provider_quality: float = 0.0
    issues: list[str] = field(default_factory=list)


DEFAULT_PROVIDER_QUALITY = {
    "manual": 0.95,
    "auto": 0.85,
    "whisper_api": 0.90,
    "whisper_local": 0.88,
    "human_upload": 0.98,
}


def score_transcript_quality(
    text: str,
    segments: list[dict] | None = None,
    provider: str = "auto",
    language: str = "en",
) -> QualityScore:
    """Score transcript quality based on content analysis."""
    score = QualityScore()
    provider_quality = DEFAULT_PROVIDER_QUALITY.get(provider, 0.8)

    if not text or not text.strip():
        score.issues.append("Empty transcript")
        score.overall = 0.0
        return score

    words = text.split()
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    word_count = len(words)
    sentence_count = len(sentences)

    score.completeness = min(1.0, word_count / 500) if word_count > 0 else 0
    score.word_accuracy = _score_word_repetition(words)
    score.sentence_accuracy = _score_sentence_length(sentences)
    score.grammar_score = _score_grammar_indicators(text)
    score.timestamp_accuracy = _score_timestamps(segments) if segments else 0.8
    score.provider_quality = provider_quality

    if word_count < 10:
        score.issues.append("Very short transcript (under 10 words)")
    if sentence_count < 3:
        score.issues.append("Fewer than 3 sentences detected")
    if word_count > 5000:
        score.issues.append("Long transcript - may need chunking")

    score.confidence = (
        score.word_accuracy * 0.25
        + score.sentence_accuracy * 0.15
        + score.grammar_score * 0.20
        + score.completeness * 0.15
        + score.timestamp_accuracy * 0.10
        + provider_quality * 0.15
    )

    score.overall = round(score.confidence, 2)
    return score


def _score_word_repetition(words: list[str]) -> float:
    if not words:
        return 0.0
    word_freq: dict[str, int] = {}
    for w in words:
        w_lower = w.lower()
        word_freq[w_lower] = word_freq.get(w_lower, 0) + 1

    total = len(words)
    repeated = sum(c for c in word_freq.values() if c > 3)
    repetition_ratio = repeated / total if total > 0 else 0

    if repetition_ratio > 0.3:
        return max(0.3, 1.0 - repetition_ratio)
    return 0.9


def _score_sentence_length(sentences: list[str]) -> float:
    if not sentences:
        return 0.0
    avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
    if avg_length < 3:
        return 0.3
    if avg_length > 50:
        return 0.5
    return 0.9


def _score_grammar_indicators(text: str) -> float:
    score = 1.0
    if not text.endswith((".", "!", "?")):
        score -= 0.1
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    if caps_ratio > 0.3:
        score -= 0.2
    return max(0.0, score)


def _score_timestamps(segments: list[dict]) -> float:
    if not segments:
        return 0.0
    valid = 0
    for seg in segments:
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        if isinstance(start, (int, float)) and isinstance(end, (int, float)):
            if 0 <= start < end:
                valid += 1
    return valid / len(segments) if segments else 0.0
