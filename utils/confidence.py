"""Confidence scoring utility for content analysis."""

from __future__ import annotations


def compute_confidence(
    word_count: int,
    sentence_count: int,
    has_entities: bool,
    has_keywords: bool,
    has_outline: bool,
) -> float:
    """Compute overall confidence score for the analysis based on transcript characteristics.

    Args:
        word_count: Number of words in transcript.
        sentence_count: Number of sentences.
        has_entities: Whether entities were extracted.
        has_keywords: Whether keywords were extracted.
        has_outline: Whether an outline was generated.

    Returns:
        Confidence score between 0.0 and 1.0.
    """
    score = 0.0

    if word_count >= 500:
        score += 0.25
    elif word_count >= 200:
        score += 0.15
    elif word_count >= 50:
        score += 0.10
    else:
        score += 0.05

    if sentence_count >= 30:
        score += 0.15
    elif sentence_count >= 10:
        score += 0.10
    else:
        score += 0.05

    if has_entities:
        score += 0.20
    if has_keywords:
        score += 0.20
    if has_outline:
        score += 0.20

    return min(round(score, 2), 1.0)


def compute_depth_score(word_count: int, entity_count: int, keyword_count: int, outline_sections: int) -> float:
    score = min(word_count / 5000 * 30, 30)
    score += min(entity_count * 5, 20)
    score += min(keyword_count * 3, 20)
    score += min(outline_sections * 10, 30)
    return min(round(score, 1), 100.0)
