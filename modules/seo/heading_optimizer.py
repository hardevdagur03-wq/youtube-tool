"""Heading optimizer — Phase 8. Analyzes heading hierarchy and keyword coverage."""

from __future__ import annotations
import re
from typing import Any

from models.blog_generation import BlogResult


def analyze(blog: BlogResult, primary_keyword: str = "") -> dict[str, Any]:
    pk = primary_keyword.lower().strip() if primary_keyword else ""
    headings: list[dict[str, Any]] = []
    h1_count = 1 if blog.seo_title else 0
    h2_count = len(blog.sections)
    h3_count = sum(len(s.subsections) for s in blog.sections)

    if blog.seo_title:
        headings.append({"level": 1, "text": blog.seo_title, "has_keyword": pk and pk in blog.seo_title.lower()})
    for s in blog.sections:
        headings.append({"level": 2, "text": s.heading, "has_keyword": pk and pk in s.heading.lower()})
        for sub in s.subsections:
            headings.append({"level": 3, "text": sub.heading, "has_keyword": pk and pk in sub.heading.lower()})

    issues: list[str] = []
    if h1_count > 1:
        issues.append("Multiple H1 headings detected")
    if h1_count == 0:
        issues.append("No H1 heading found")
    if h2_count == 0:
        issues.append("No H2 headings found — add structural sections")
    if h2_count > 0 and pk:
        kw_in_heading = any(pk in h["text"].lower() for h in headings if h["level"] >= 2)
        if not kw_in_heading:
            issues.append("Primary keyword not found in any H2/H3 heading")

    return {
        "h1_count": h1_count,
        "h2_count": h2_count,
        "h3_count": h3_count,
        "headings": headings,
        "issues": issues,
    }
