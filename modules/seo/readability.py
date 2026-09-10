"""Readability analysis — Phase 8. Computes Flesch Reading Ease and content statistics."""

from __future__ import annotations
import re
from typing import Any

from models.blog_generation import BlogResult


def analyze(blog: BlogResult) -> dict[str, Any]:
    text = " ".join([
        blog.introduction,
        " ".join(s.content for s in blog.sections),
        " ".join(sub.content for s in blog.sections for sub in s.subsections),
        blog.conclusion,
    ])
    words = text.split()
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    paragraphs = [p for p in text.split("\n\n") if p.strip()]

    wc = len(words)
    cc = len(text)
    pc = max(len(paragraphs), 1)
    sc = max(len(sentences), 1)

    avg_sentence_length = round(wc / sc, 1) if sc else 0
    syllable_count = _count_syllables(text)
    flesch = _flesch_reading_ease(wc, sc, syllable_count)
    passive_pct = _passive_voice_pct(text)
    reading_time = f"{max(1, round(wc / 200))} min" if wc >= 200 else "< 1 min"
    grade_level = _grade_level(flesch)

    return {
        "word_count": wc,
        "character_count": cc,
        "paragraph_count": pc,
        "avg_sentence_length": avg_sentence_length,
        "flesch_reading_ease": round(flesch, 1),
        "grade_level": grade_level,
        "passive_voice_pct": round(passive_pct, 1),
        "reading_time": reading_time,
    }


def _count_syllables(text: str) -> int:
    words = re.findall(r"[a-z]+", text.lower())
    count = 0
    for w in words:
        if len(w) <= 3:
            count += 1
            continue
        vowels = len(re.findall(r"[aeiouy]+", w))
        count += max(vowels, 1)
    return max(count, 1)


def _flesch_reading_ease(word_count: int, sentence_count: int, syllable_count: int) -> float:
    if word_count == 0 or sentence_count == 0:
        return 0.0
    return 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (syllable_count / word_count)


def _passive_voice_pct(text: str) -> float:
    passive = re.findall(r"\b(am|is|are|was|were|be|been|being)\s+\w+ed\b", text.lower())
    words = text.split()
    return (len(passive) / len(words)) * 100 if words else 0.0


def _grade_level(flesch: float) -> str:
    if flesch >= 90:
        return "5th grade"
    if flesch >= 80:
        return "6th grade"
    if flesch >= 70:
        return "7th grade"
    if flesch >= 60:
        return "8th-9th grade"
    if flesch >= 50:
        return "10th-12th grade"
    if flesch >= 30:
        return "College"
    return "College Graduate"
