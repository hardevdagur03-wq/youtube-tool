"""Keyword optimizer — Phase 7. Analyzes keyword usage in generated content."""

from __future__ import annotations
import re
from typing import Any

from models.blog_generation import BlogResult


class KeywordOptimizer:
    """Analyzes keyword density, placement, and distribution."""

    def __init__(self, primary: str = "", secondary: list[str] | None = None) -> None:
        self.primary = primary.lower().strip() if primary else ""
        self.secondary = [k.lower().strip() for k in (secondary or []) if k.strip()]

    def analyze(self, blog: BlogResult) -> dict[str, Any]:
        full = self._text(blog)
        wc = len(full.split())
        result: dict[str, Any] = {
            "primary_keyword": self.primary,
            "density_pct": 0.0,
            "in_title": False,
            "in_intro": False,
            "in_headings": [],
            "in_first_200_words": False,
            "in_url_slug": False,
            "in_meta_description": False,
            "secondary_found": [],
            "secondary_missing": [],
            "suggestions": [],
        }

        if not self.primary or wc == 0:
            return result

        count = full.lower().count(self.primary)
        result["density_pct"] = round((count / wc) * 100, 2)
        result["in_title"] = self.primary in blog.seo_title.lower()
        result["in_intro"] = self.primary in blog.introduction.lower()
        result["in_url_slug"] = self.primary.replace(" ", "-") in blog.slug.lower() or self.primary in blog.slug.lower().replace("-", " ")
        result["in_meta_description"] = self.primary in blog.meta_description.lower()

        first_200 = " ".join(full.split()[:200]).lower()
        result["in_first_200_words"] = self.primary in first_200

        for i, s in enumerate(blog.sections):
            if self.primary in s.heading.lower():
                result["in_headings"].append(s.heading)

        for kw in self.secondary:
            if kw in full.lower():
                result["secondary_found"].append(kw)
            else:
                result["secondary_missing"].append(kw)

        if result["density_pct"] > 3.0:
            result["suggestions"].append("Keyword density > 3% — consider reducing usage")
        elif result["density_pct"] < 0.5:
            result["suggestions"].append("Keyword density < 0.5% — consider increasing natural usage")

        if not result["in_title"]:
            result["suggestions"].append("Add primary keyword to title")
        if not result["in_intro"]:
            result["suggestions"].append("Add primary keyword to introduction")
        if not result["in_meta_description"]:
            result["suggestions"].append("Add primary keyword to meta description")
        if result["secondary_missing"]:
            result["suggestions"].append(f"Missing secondary keywords: {', '.join(result['secondary_missing'][:3])}")

        return result

    def _text(self, blog: BlogResult) -> str:
        parts = [blog.seo_title, blog.introduction]
        for s in blog.sections:
            parts.append(s.content)
            for sub in s.subsections:
                parts.append(sub.content)
        parts.append(blog.conclusion)
        return " ".join(parts)
