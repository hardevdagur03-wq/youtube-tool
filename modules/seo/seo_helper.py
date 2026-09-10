"""SEO helper — Phase 7. Scoring, validation, keyword analysis."""

from __future__ import annotations
import re
from typing import Any

from models.blog_generation import BlogResult


def estimate_score(blog: BlogResult, primary_keyword: str = "") -> float:
    """Estimate SEO score (0-100) based on content quality signals."""
    full_text = _full_text(blog)
    wc = len(full_text.split())
    scores = {
        "title": _score_title(blog.seo_title, primary_keyword),
        "meta": 10.0 if blog.meta_description and 140 <= len(blog.meta_description) <= 165 else 0.0,
        "headings": _score_headings(blog),
        "length": _score_length(wc),
        "keyword": _score_kw(full_text, primary_keyword),
        "intro": _score_intro(blog.introduction, primary_keyword),
        "faq": 10.0 if len(blog.faq) >= 3 else (5.0 if blog.faq else 0.0),
        "conclusion": 8.0 if len(blog.conclusion.split()) >= 40 else 0.0,
        "cta": 5.0 if len(blog.call_to_action.split()) >= 8 else 0.0,
        "toc": 5.0 if len(blog.table_of_contents) >= 3 else 0.0,
    }
    return round(min(sum(scores.values()), 100.0), 1)


def _full_text(blog: BlogResult) -> str:
    parts = [blog.seo_title, blog.introduction]
    for s in blog.sections:
        parts.append(s.content)
        for sub in s.subsections:
            parts.append(sub.content)
    parts.append(blog.conclusion)
    return " ".join(parts)


def _score_title(title: str, kw: str) -> float:
    if not title:
        return 0.0
    s = 5.0
    if 30 <= len(title) <= 60:
        s += 8.0
    if kw and kw.lower() in title.lower():
        s += 7.0
    return min(s, 15.0)


def _score_headings(blog: BlogResult) -> float:
    h2 = len(blog.sections)
    if h2 >= 4:
        return 12.0
    if h2 >= 2:
        return 8.0
    return 4.0 if h2 >= 1 else 0.0


def _score_length(wc: int) -> float:
    if wc >= 2000:
        return 15.0
    if wc >= 1200:
        return 12.0
    if wc >= 800:
        return 8.0
    if wc >= 400:
        return 5.0
    return 0.0


def _score_kw(text: str, kw: str) -> float:
    if not kw:
        return 0.0
    cnt = text.lower().count(kw.lower())
    if 2 <= cnt <= 8:
        return 10.0
    if cnt > 8:
        return 5.0
    return 2.0 if cnt >= 1 else 0.0


def _score_intro(intro: str, kw: str) -> float:
    if not intro:
        return 0.0
    wc = len(intro.split())
    s = 2.0
    if wc >= 50:
        s += 4.0
    elif wc >= 30:
        s += 2.0
    if kw and kw.lower() in intro.lower():
        s += 4.0
    return min(s, 10.0)


def validate(blog: BlogResult) -> list[str]:
    warnings: list[str] = []
    if not blog.seo_title:
        warnings.append("Missing title")
    if not blog.meta_description:
        warnings.append("Missing meta description")
    if not blog.slug:
        warnings.append("Missing slug")
    if not blog.table_of_contents:
        warnings.append("Missing TOC")
    if not blog.faq:
        warnings.append("Missing FAQ")
    if not blog.call_to_action:
        warnings.append("Missing CTA")
    if not blog.conclusion:
        warnings.append("Missing conclusion")
    return warnings
