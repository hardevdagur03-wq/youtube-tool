"""Keyword Analyzer — dedicated keyword density, placement, LSI coverage, and stuffing detection."""

from __future__ import annotations
import re
from review.base import BaseValidator
from models.blog_review import BlogReviewRequest
from review.review_models_ext import KeywordReport


LSI_KEYWORDS: dict[str, list[str]] = {
    "python": ["programming", "language", "code", "script", "development", "software", "library", "framework", "automation", "data"],
    "testing": ["quality", "verification", "validation", "bug", "coverage", "assertion", "unit", "integration", "regression", "debug"],
    "machine learning": ["ai", "artificial intelligence", "model", "training", "algorithm", "prediction", "classification", "neural", "data", "pattern"],
    "web development": ["frontend", "backend", "api", "responsive", "framework", "database", "server", "client", "http", "css"],
    "data science": ["analytics", "statistics", "visualization", "insights", "dataset", "analysis", "mining", "pipeline", "etl", "dashboard"],
}


class KeywordAnalyzer(BaseValidator):
    """Analyzes keyword density, placement, LSI coverage, and stuffing."""

    def name(self) -> str:
        return "Keyword Analysis"

    def validate(self, request: BlogReviewRequest) -> KeywordReport:
        text = request.content
        if not text:
            return KeywordReport(score=100.0)

        primary_kw = request.primary_keyword.lower().strip() if request.primary_keyword else ""
        secondary_kws = [kw.lower().strip() for kw in request.secondary_keywords if kw.strip()]

        words = text.split()
        total_words = len(words) if words else 1
        text_lower = text.lower()

        issues: list[str] = []

        # Primary keyword density
        primary_count = 0
        if primary_kw:
            primary_count = len(re.findall(re.escape(primary_kw), text_lower))
        primary_density = (primary_count * len(primary_kw.split()) / total_words) if primary_kw else 0

        # Secondary keyword density
        secondary_density: dict[str, float] = {}
        for sk in secondary_kws:
            sk_count = len(re.findall(re.escape(sk), text_lower))
            density = (sk_count * len(sk.split()) / total_words) if total_words else 0
            secondary_density[sk] = round(density * 100, 2)

        # Keyword placement
        paragraphs = [p for p in re.split(r'\n\s*\n', text) if p.strip()]
        first_para = paragraphs[0].lower() if paragraphs else ""
        last_para = paragraphs[-1].lower() if paragraphs else ""

        kw_in_title = bool(primary_kw and request.blog_title and primary_kw in request.blog_title.lower())
        kw_in_first_para = primary_kw and primary_kw in first_para
        kw_in_last_para = primary_kw and primary_kw in last_para

        # Check headings for keyword
        headings = re.findall(r'^#{1,6}\s+(.+)$', text, re.MULTILINE)
        kw_in_headings = any(primary_kw in h.lower() for h in headings) if primary_kw else False

        # Keyword stuffing detection
        stuffing = False
        if primary_kw:
            expected_max = max(1, total_words * 0.025)
            stuffing = primary_count > expected_max
            if stuffing:
                issues.append(f"Keyword stuffing detected: '{primary_kw}' appears {primary_count} times ({primary_density*100:.2f}%)")

        # Recommended density range
        if primary_kw:
            if primary_density < 0.005:
                issues.append(f"Keyword density too low ({primary_density*100:.2f}%). Aim for 0.5-2.5%")
            elif primary_density > 0.03:
                issues.append(f"Keyword density too high ({primary_density*100:.2f}%). Reduce to avoid stuffing penalty")

        # Secondary keyword checks
        for sk in secondary_kws:
            if sk not in text_lower:
                issues.append(f"Secondary keyword '{sk}' not found in content")

        # LSI keyword analysis
        lsi_found: list[str] = []
        lsi_missing: list[str] = []
        if primary_kw:
            for base_kw, related_kws in LSI_KEYWORDS.items():
                if base_kw in primary_kw or primary_kw in base_kw:
                    for rk in related_kws:
                        if rk in text_lower:
                            lsi_found.append(rk)
                        else:
                            lsi_missing.append(rk)
                    break

        # Score calculation
        score = 100.0
        if primary_kw:
            if not kw_in_title:
                score -= 10
                issues.append("Primary keyword not found in title")
            if not kw_in_first_para:
                score -= 5
                issues.append("Primary keyword not found in first paragraph")
            if not kw_in_last_para:
                score -= 3
                issues.append("Primary keyword not found in conclusion paragraph")
            if not kw_in_headings:
                score -= 5
                issues.append("Primary keyword not found in any heading")
            if stuffing:
                score -= 15
            if primary_density < 0.005:
                score -= 10
            if len(lsi_missing) > 3:
                score -= 5
        else:
            issues.append("No primary keyword specified")

        for sk in secondary_kws:
            if sk not in text_lower:
                score -= 3

        score = max(0, min(100, score))

        return KeywordReport(
            score=round(score, 1),
            primary_keyword_density=round(primary_density * 100, 2),
            secondary_keyword_density=secondary_density,
            keyword_in_title=kw_in_title,
            keyword_in_first_paragraph=kw_in_first_para,
            keyword_in_last_paragraph=kw_in_last_para,
            keyword_in_headings=kw_in_headings,
            keyword_stuffing_detected=stuffing,
            lsi_keywords_found=lsi_found,
            lsi_keywords_missing=lsi_missing,
            issues=issues,
        )
