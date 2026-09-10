"""SEO score — Phase 8. Multi-dimensional SEO quality scoring engine."""

from __future__ import annotations
from typing import Any

from models.blog_generation import BlogResult
from modules.seo.readability import analyze as readability_analyze


def compute(blog: BlogResult, primary_keyword: str = "", analysis_data: dict[str, Any] | None = None) -> dict[str, Any]:
    full = _full_text(blog)
    wc = len(full.split())
    pk = primary_keyword.lower().strip() if primary_keyword else ""
    ka = analysis_data or {}

    scores: dict[str, float] = {
        "title": _title_score(blog.seo_title, pk),
        "description": _desc_score(blog.meta_description, pk),
        "keyword": _keyword_score(full, pk, ka),
        "headings": _heading_score(blog),
        "structure": _structure_score(blog),
        "content": _content_score(wc),
        "readability": _readability_score(blog),
        "faq": _faq_score(blog),
        "links": _link_score(ka),
        "schema": _schema_score(ka),
    }

    total = round(min(sum(scores.values()), 100.0), 1)
    return {
        "score": total,
        "components": scores,
        "max_score": 100.0,
    }


def _full_text(blog: BlogResult) -> str:
    parts = [blog.seo_title, blog.introduction]
    for s in blog.sections:
        parts.append(s.content)
        for sub in s.subsections:
            parts.append(sub.content)
    parts.append(blog.conclusion)
    return " ".join(parts)


def _title_score(title: str, pk: str) -> float:
    if not title:
        return 0.0
    s = 2.0
    if 30 <= len(title) <= 60:
        s += 5.0
    if pk and pk in title.lower():
        s += 4.0
    if any(c in "?!:;" for c in title):
        s += 1.0
    return min(s, 10.0)


def _desc_score(desc: str, pk: str) -> float:
    if not desc:
        return 0.0
    s = 2.0
    if 140 <= len(desc) <= 165:
        s += 4.0
    elif len(desc) >= 120:
        s += 2.0
    if pk and pk in desc.lower():
        s += 4.0
    return min(s, 10.0)


def _keyword_score(text: str, pk: str, ka: dict) -> float:
    s = 2.0
    if not pk or not text:
        return 0.0
    density = ka.get("density", {}).get("primary", 0) if isinstance(ka.get("density"), dict) else 0
    if 0.5 <= density <= 3.0:
        s += 4.0
    elif density > 0:
        s += 2.0
    if ka.get("in_title"):
        s += 2.0
    if ka.get("in_intro"):
        s += 2.0
    if ka.get("in_headings"):
        s += 2.0
    return min(s, 15.0)


def _heading_score(blog: BlogResult) -> float:
    h2 = len(blog.sections)
    h3 = sum(len(s.subsections) for s in blog.sections)
    s = 0.0
    if h2 >= 4:
        s += 8.0
    elif h2 >= 2:
        s += 5.0
    elif h2 >= 1:
        s += 2.0
    if h3 >= 3:
        s += 4.0
    elif h3 >= 1:
        s += 2.0
    return min(s, 12.0)


def _structure_score(blog: BlogResult) -> float:
    s = 2.0
    if blog.table_of_contents:
        s += 2.0
    if blog.call_to_action:
        s += 2.0
    if blog.conclusion:
        s += 2.0
    return min(s, 8.0)


def _content_score(wc: int) -> float:
    if wc >= 2000:
        return 12.0
    if wc >= 1200:
        return 10.0
    if wc >= 800:
        return 7.0
    if wc >= 400:
        return 4.0
    return 0.0


def _readability_score(blog: BlogResult) -> float:
    r = readability_analyze(blog)
    s = 2.0
    flesch = r.get("flesch_reading_ease", 0)
    if flesch >= 80:
        s += 6.0
    elif flesch >= 60:
        s += 4.0
    elif flesch >= 40:
        s += 2.0
    avg_sen = r.get("avg_sentence_length", 30)
    if 12 <= avg_sen <= 22:
        s += 3.0
    return min(s, 10.0)


def _faq_score(blog: BlogResult) -> float:
    n = len(blog.faq)
    if n >= 5:
        return 8.0
    if n >= 3:
        return 5.0
    if n >= 1:
        return 3.0
    return 0.0


def _link_score(ka: dict) -> float:
    return 5.0


def _schema_score(ka: dict) -> float:
    return 5.0
