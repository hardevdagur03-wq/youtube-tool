"""Blog Quality Evaluator — multi-dimensional quality scoring for generated content.

Evaluates: grammar, SEO, readability, fact accuracy, brand voice, structure, 
originality, EEAT compliance, and engagement potential.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BlogQualityScore:
    overall: float = 0.0
    grammar_score: float = 0.0
    seo_score: float = 0.0
    readability_score: float = 0.0
    fact_accuracy: float = 0.0
    brand_voice: float = 0.0
    structure_score: float = 0.0
    originality_score: float = 0.0
    eeat_score: float = 0.0
    engagement_score: float = 0.0
    word_count: int = 0
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


_MIN_WORD_COUNT = 300
_IDEAL_WORD_COUNT = 2000
_MAX_SENTENCE_WORDS = 30
_MAX_PARAGRAPH_SENTENCES = 5


def evaluate_blog_quality(
    content: str,
    title: str = "",
    meta_description: str = "",
    headings: list[str] | None = None,
    keywords: list[str] | None = None,
) -> BlogQualityScore:
    """Evaluate blog content quality across multiple dimensions."""
    score = BlogQualityScore()

    if not content or not content.strip():
        score.issues.append("Empty content")
        return score

    words = content.split()
    sentences = re.split(r"[.!?]+", content)
    sentences = [s.strip() for s in sentences if s.strip()]
    paragraphs = [p for p in content.split("\n\n") if p.strip()]

    score.word_count = len(words)

    score.grammar_score = _evaluate_grammar(content, sentences)
    score.readability_score = _evaluate_readability(sentences, words)
    score.structure_score = _evaluate_structure(
        content, headings or [], paragraphs, sentences
    )
    score.seo_score = _evaluate_seo(
        title, meta_description, headings or [], keywords or [], words
    )
    score.originality_score = _evaluate_originality(content)
    score.engagement_score = _evaluate_engagement(content, sentences)
    score.eeat_score = _evaluate_eeat(content, words, sentences)
    score.fact_accuracy = _evaluate_factual_support(content)

    scores = [
        score.grammar_score * 0.20,
        score.readability_score * 0.15,
        score.structure_score * 0.15,
        score.seo_score * 0.20,
        score.originality_score * 0.10,
        score.engagement_score * 0.10,
        score.eeat_score * 0.05,
        score.fact_accuracy * 0.05,
    ]
    score.overall = round(sum(scores), 2)

    _add_quality_issues(score, words, sentences, paragraphs)
    _add_quality_suggestions(score, words, sentences, headings or [], keywords or [])

    return score


def _evaluate_grammar(content: str, sentences: list[str]) -> float:
    score = 1.0

    caps_words = sum(1 for w in content.split() if w.isupper() and len(w) > 1)
    caps_ratio = caps_words / max(len(content.split()), 1)
    if caps_ratio > 0.1:
        score -= 0.1

    sentences_starting_lower = sum(
        1 for s in sentences if s and s[0].islower()
    )
    if sentences_starting_lower > 0:
        score -= 0.05 * min(sentences_starting_lower, 5)

    if content.endswith((".", "!", "?")):
        score -= 0.0
    else:
        score -= 0.05

    return max(0.3, min(1.0, score))


def _evaluate_readability(sentences: list[str], words: list[str]) -> float:
    if not sentences or not words:
        return 0.0

    avg_words_per_sentence = len(words) / max(len(sentences), 1)
    if avg_words_per_sentence < 10:
        readability = 0.95
    elif avg_words_per_sentence < 20:
        readability = 0.85
    elif avg_words_per_sentence < 30:
        readability = 0.70
    else:
        readability = 0.40

    long_words = sum(1 for w in words if len(w) > 6)
    long_word_ratio = long_words / max(len(words), 1)
    if long_word_ratio > 0.3:
        readability -= 0.1

    return max(0.2, min(1.0, readability))


def _evaluate_structure(
    content: str,
    headings: list[str],
    paragraphs: list[str],
    sentences: list[str],
) -> float:
    score = 0.5

    if headings:
        score += 0.15
        has_h1 = any(h.startswith("# ") for h in headings)
        has_h2 = any(h.startswith("## ") for h in headings)
        if has_h1:
            score += 0.10
        if has_h2:
            score += 0.10

    if len(paragraphs) >= 3:
        score += 0.10

    avg_par_sentences = len(sentences) / max(len(paragraphs), 1)
    if 2 <= avg_par_sentences <= _MAX_PARAGRAPH_SENTENCES:
        score += 0.05

    return min(1.0, score)


def _evaluate_seo(
    title: str,
    meta_description: str,
    headings: list[str],
    keywords: list[str],
    words: list[str],
) -> float:
    score = 0.4

    word_count = len(words)

    if word_count >= _MIN_WORD_COUNT:
        score += 0.10
    if word_count >= _IDEAL_WORD_COUNT:
        score += 0.05

    if title and 30 <= len(title) <= 60:
        score += 0.10
    if meta_description and 120 <= len(meta_description) <= 160:
        score += 0.10

    if headings:
        score += 0.05

    if keywords:
        keyword_matches = sum(
            1 for kw in keywords
            if kw.lower() in " ".join(words[:100]).lower()
        )
        if keyword_matches >= 1:
            score += 0.10
        if keyword_matches >= 3:
            score += 0.10

    text_lower = " ".join(words).lower()
    for kw in (keywords or []):
        if kw.lower() in text_lower:
            score += 0.05
            break

    return min(1.0, score)


def _evaluate_originality(content: str) -> float:
    sentences = re.split(r"[.!?]+", content)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return 0.5

    seen = set()
    duplicates = 0
    for s in sentences:
        s_lower = s.lower()[:50]
        if s_lower in seen:
            duplicates += 1
        seen.add(s_lower)

    duplicate_ratio = duplicates / max(len(sentences), 1)
    score = 1.0 - duplicate_ratio

    words = content.split()
    unique_words = len(set(w.lower() for w in words))
    unique_ratio = unique_words / max(len(words), 1)
    if unique_ratio < 0.4:
        score -= 0.1

    return max(0.3, min(1.0, score))


def _evaluate_engagement(content: str, sentences: list[str]) -> float:
    score = 0.5

    question_count = content.count("?")
    if question_count >= 2:
        score += 0.10

    cta_patterns = [
        r"\blearn\s+more\b",
        r"\bsign\s+up\b",
        r"\btry\s+it\b",
        r"\bget\s+started\b",
        r"\bcontact\s+us\b",
        r"\bsubscribe\b",
        r"\bdownload\b",
    ]
    for pattern in cta_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            score += 0.05
            break

    list_count = content.count("\n- ") + content.count("\n* ")
    if list_count >= 1:
        score += 0.05

    bold_count = content.count("**")
    if bold_count >= 2:
        score += 0.05

    link_count = len(re.findall(r"\[.*?\]\(.*?\)", content))
    if link_count >= 2:
        score += 0.05

    return min(1.0, score)


def _evaluate_eeat(content: str, words: list[str], sentences: list[str]) -> float:
    score = 0.5

    authority_patterns = [
        r"\baccording\s+to\b",
        r"\bresearch\b",
        r"\bstudy\b",
        r"\bdata\b",
        r"\bsource\b",
        r"\bevidence\b",
        r"\bexpert\b",
        r"\bpublished\b",
    ]
    for pattern in authority_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            score += 0.05

    link_count = len(re.findall(r"\[.*?\]\(.*?\)", content))
    if link_count >= 3:
        score += 0.10

    if len(sentences) >= 10:
        score += 0.05

    return min(1.0, score)


def _evaluate_factual_support(content: str) -> float:
    score = 0.7

    citation_patterns = [
        r"\[\d+\]",
        r"\(.*?\d{4}.*?\)",
        r"\(https?://",
        r"\[.*?\]\(https?://",
    ]
    for pattern in citation_patterns:
        if re.search(pattern, content):
            score += 0.10
            break

    if re.search(r"\bsource\b|\baccording\b|\bcited\b", content, re.IGNORECASE):
        score += 0.10

    return min(1.0, score)


def _add_quality_issues(
    score: BlogQualityScore, words: list[str],
    sentences: list[str], paragraphs: list[str],
) -> None:
    if len(words) < _MIN_WORD_COUNT:
        score.issues.append(f"Content too short ({len(words)} words, min {_MIN_WORD_COUNT})")

    avg_sentence_len = len(words) / max(len(sentences), 1)
    if avg_sentence_len > _MAX_SENTENCE_WORDS:
        score.issues.append(f"Average sentence too long ({avg_sentence_len:.0f} words)")

    passive_count = len(re.findall(r"\b(is|are|was|were|been|being)\s+\w+ed\b", " ".join(words)))
    if passive_count > len(sentences) * 0.3:
        score.issues.append("High passive voice usage")

    if len(paragraphs) < 2:
        score.issues.append("Too few paragraphs")

    exclamation_count = " ".join(words).count("!")
    if exclamation_count > 5:
        score.issues.append("Excessive exclamation marks")


def _add_quality_suggestions(
    score: BlogQualityScore, words: list[str],
    sentences: list[str], headings: list[str],
    keywords: list[str],
) -> None:
    if len(words) < _IDEAL_WORD_COUNT:
        score.suggestions.append(
            f"Consider expanding content to {_IDEAL_WORD_COUNT} words"
        )

    if not headings:
        score.suggestions.append("Add heading structure (H1, H2, H3)")

    if keywords and not any(
        kw.lower() in " ".join(words).lower() for kw in keywords
    ):
        score.suggestions.append("Include target keywords in content")

    avg_sentence_len = len(words) / max(len(sentences), 1)
    if avg_sentence_len > 25:
        score.suggestions.append("Shorten some sentences for better readability")

    if not re.search(r"\?|\!|\"", " ".join(words)):
        score.suggestions.append("Add rhetorical questions or pull quotes for engagement")
