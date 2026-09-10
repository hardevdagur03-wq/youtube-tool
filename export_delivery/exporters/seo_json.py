"""SEO JSON Exporter — generates standalone SEO analysis reports.

Produces a structured JSON file with SEO score, keyword analysis,
heading analysis, image alt text analysis, and link analysis.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from export_delivery.models import TemplateConfig

logger = logging.getLogger(__name__)


class SEOJSONExporter:
    """Generates standalone SEO analysis JSON files.

    Outputs: seo.json with full SEO metrics for integration
    with SEO tools and analytics platforms.
    """

    def export(
        self,
        document: Any,
        output_dir: str = "",
        template_config: TemplateConfig | None = None,
    ) -> dict[str, Any]:
        """Export SEO analysis as JSON.

        Args:
            document: Document-like object.
            output_dir: Output directory.
            template_config: Unused for SEO JSON.

        Returns:
            Dict with file info.
        """
        output_dir = output_dir or os.path.join(
            os.getcwd(), "exports_delivery", getattr(document, "project_id", "unknown")
        )
        os.makedirs(output_dir, exist_ok=True)

        seo_data = self._build_seo_data(document)
        slug = getattr(document, "slug", "") or self._slugify(getattr(document, "title", "export"))
        filename = f"{slug}-seo.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(seo_data, f, indent=2, default=str)

        size = os.path.getsize(filepath)
        logger.info("SEO JSON exported: %s (%d bytes)", filename, size)

        return {
            "format": "seo_json",
            "filename": filename,
            "filepath": filepath,
            "size_bytes": size,
            "mime_type": "application/json",
        }

    def _build_seo_data(self, document: Any) -> dict[str, Any]:
        """Build structured SEO data from document."""
        title = getattr(document, "title", "")
        content = getattr(document, "content", "") or ""
        sections = getattr(document, "sections", []) or []
        tags = getattr(document, "tags", []) or []
        meta_desc = getattr(document, "meta_description", "")
        word_count = getattr(document, "word_count", 0) or len(content.split())
        reading_time = getattr(document, "reading_time", 0) or max(1, word_count // 200)
        category = getattr(document, "category", "")
        author = getattr(document, "author", "")

        # Extract keywords from tags and content
        focus_keyword = tags[0] if tags else (title.split()[0] if title else "")
        keyword_density = self._calculate_keyword_density(content, focus_keyword)

        # Heading analysis
        headings = self._extract_headings(content, sections)
        h1_count = sum(1 for h in headings if h["level"] == 1)
        h2_count = sum(1 for h in headings if h["level"] == 2)
        h3_count = sum(1 for h in headings if h["level"] == 3)

        # Link analysis
        internal_links = getattr(document, "internal_links", []) or []
        external_links = getattr(document, "external_links", []) or []
        refs = getattr(document, "references", []) or []

        # Compute SEO score
        seo_score = self._compute_seo_score(
            title=bool(title),
            meta_desc=bool(meta_desc),
            h1_count=h1_count,
            h2_count=h2_count,
            word_count=word_count,
            keyword_density=keyword_density,
            has_images=bool(getattr(document, "images", None)),
            has_faq=bool(getattr(document, "faq", None)),
        )

        return {
            "seo_score": round(seo_score, 1),
            "seo_grade": self._grade(seo_score),
            "focus_keyword": focus_keyword,
            "keyword_density": round(keyword_density, 4),
            "word_count": word_count,
            "reading_time_minutes": reading_time,
            "content_score": round(min(100, seo_score * 1.1), 1),
            "meta": {
                "title": title,
                "title_length": len(title),
                "description": meta_desc,
                "description_length": len(meta_desc),
                "slug": getattr(document, "slug", "") or self._slugify(title),
                "canonical_url": getattr(document, "base_url", "") + "/" + self._slugify(title) if getattr(document, "base_url", "") else "",
            },
            "headings": {
                "total": len(headings),
                "h1_count": h1_count,
                "h2_count": h2_count,
                "h3_count": h3_count,
                "issues": self._check_heading_issues(headings),
            },
            "keywords": {
                "primary": focus_keyword,
                "secondary": tags[1:5] if len(tags) > 1 else [],
                "tags": tags,
                "category": category,
            },
            "links": {
                "internal_count": len(internal_links),
                "external_count": len(external_links) + len(refs),
            },
            "readability": {
                "word_count": word_count,
                "reading_time_minutes": reading_time,
                "sentence_count": len(content.split(". ")) if content else 0,
            },
            "authors": [author] if author else [],
            "schema_types": ["Article"],
        }

    def _extract_headings(self, content: str, sections: list) -> list[dict]:
        """Extract heading structure from content."""
        import re
        headings = []

        # From sections
        for section in sections:
            heading = section.get("heading", "") if isinstance(section, dict) else getattr(section, "heading", "")
            level = section.get("level", 2) if isinstance(section, dict) else 2
            if heading:
                headings.append({"level": level, "text": heading})
            for sub in (section.get("subsections", []) if isinstance(section, dict) else getattr(section, "subsections", [])):
                sub_h = sub.get("heading", "") if isinstance(sub, dict) else getattr(sub, "heading", "")
                if sub_h:
                    headings.append({"level": level + 1, "text": sub_h})

        return headings

    def _check_heading_issues(self, headings: list[dict]) -> list[str]:
        """Check for heading hierarchy issues."""
        issues = []
        prev_level = 0
        for h in headings:
            if h["level"] > prev_level + 1 and prev_level > 0:
                issues.append(f"Skipped heading level: H{prev_level} → H{h['level']}")
            prev_level = h["level"]
        if not headings:
            issues.append("No headings found in content")
        return issues

    @staticmethod
    def _calculate_keyword_density(content: str, keyword: str) -> float:
        """Calculate keyword density as a ratio."""
        if not content or not keyword:
            return 0.0
        words = content.lower().split()
        if not words:
            return 0.0
        keyword_lower = keyword.lower()
        keyword_count = sum(1 for w in words if keyword_lower in w)
        return keyword_count / len(words)

    @staticmethod
    def _compute_seo_score(
        title: bool, meta_desc: bool, h1_count: int, h2_count: int,
        word_count: int, keyword_density: float, has_images: bool, has_faq: bool,
    ) -> float:
        """Compute overall SEO score (0-100)."""
        score = 50.0
        if title:
            score += 10
        if meta_desc:
            score += 10
        if h1_count == 1:
            score += 5
        elif h1_count == 0:
            score -= 5
        if h2_count >= 2:
            score += 5
        if word_count >= 300:
            score += 5
        if 0.005 <= keyword_density <= 0.03:
            score += 5
        elif keyword_density > 0.05:
            score -= 5
        if has_images:
            score += 5
        if has_faq:
            score += 5
        return max(0, min(100, score))

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 90:
            return "excellent"
        if score >= 70:
            return "good"
        if score >= 50:
            return "fair"
        return "poor"

    @staticmethod
    def _slugify(text: str) -> str:
        if not text:
            return "untitled"
        slug = text.lower().strip().replace(" ", "-").replace("_", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        return slug.strip("-") or "untitled"
