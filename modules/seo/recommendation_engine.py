"""Recommendation engine — Phase 8. Generates prioritized SEO recommendations."""

from __future__ import annotations
from typing import Any

from models.blog_generation import BlogResult


def generate(blog: BlogResult, scores: dict[str, Any], keyword_analysis: dict[str, Any] | None = None) -> list[dict[str, str]]:
    recs: list[dict[str, str]] = []
    ka = keyword_analysis or {}
    components = scores.get("components", {})

    if components.get("title", 10) < 7:
        recs.append(_rec("high", "title", "Title needs optimization. Include primary keyword near the beginning and keep 50-60 characters."))
    if components.get("description", 10) < 7:
        recs.append(_rec("high", "meta_description", "Meta description should be 150-165 characters with primary keyword and a compelling CTA."))
    if not blog.meta_description:
        recs.append(_rec("critical", "meta_description", "Meta description is missing. This is essential for search result CTR."))
    if not blog.slug:
        recs.append(_rec("high", "slug", "URL slug is missing. Generate an SEO-friendly slug from the title."))
    if not ka.get("in_title"):
        recs.append(_rec("high", "keyword_title", "Primary keyword not found in the title. Add it naturally for better ranking."))
    if not ka.get("in_intro"):
        recs.append(_rec("high", "keyword_intro", "Primary keyword not found in the introduction. Include it in the first paragraph."))
    if not ka.get("in_meta"):
        recs.append(_rec("medium", "keyword_meta", "Primary keyword not in meta description."))
    if components.get("headings", 12) < 8:
        recs.append(_rec("medium", "headings", "More H2/H3 headings improve scannability and SEO. Aim for 4+ H2 sections."))
    if components.get("faq", 8) < 3:
        recs.append(_rec("low", "faq", "FAQ section could be expanded. 5+ FAQ items improve voice search visibility."))
    if components.get("content", 12) < 7:
        recs.append(_rec("medium", "content_length", "Content is shorter than recommended. Aim for 1200+ words for better SEO."))
    if not blog.call_to_action:
        recs.append(_rec("medium", "cta", "Call to action is missing. Add one to improve engagement."))
    if not blog.table_of_contents:
        recs.append(_rec("low", "toc", "Table of contents would improve navigation and user experience."))

    flesch = _get_readability_score(blog)
    if flesch < 40:
        recs.append(_rec("medium", "readability", "Content is difficult to read (Flesch score < 40). Simplify sentences and use shorter words."))
    elif flesch < 60:
        recs.append(_rec("low", "readability", "Readability could be improved. Target Flesch score of 60+ for general audiences."))

    return recs


def _rec(priority: str, category: str, message: str) -> dict[str, str]:
    return {"priority": priority, "category": category, "message": message, "suggestion": message}


def _get_readability_score(blog: BlogResult) -> float:
    try:
        from modules.seo.readability import analyze as r_analyze
        r = r_analyze(blog)
        return r.get("flesch_reading_ease", 0.0)
    except Exception:
        return 0.0
