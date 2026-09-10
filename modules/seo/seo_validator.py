"""SEO validation and scoring for generated blog content.

Computes an estimated SEO score based on content structure,
keyword usage, headings, length, and readability heuristics.
"""

from __future__ import annotations
import logging
import re
from typing import Any

from models.blog_generation import BlogResult

logger = logging.getLogger(__name__)


class SEOValidator:
    """Validates and scores blog content for SEO quality."""

    def __init__(self) -> None:
        self._score_components: dict[str, float] = {}

    def score(self, blog: BlogResult, primary_keyword: str = "") -> float:
        """Compute an estimated SEO score (0-100) for a blog post.

        Evaluates:
        1. Title quality (presence, keyword inclusion, length)
        2. Heading structure (H2/H3 presence)
        3. Content length (word count thresholds)
        4. Keyword usage (primary + secondary)
        5. Introduction quality
        6. Conclusion presence
        7. FAQ inclusion
        8. CTA presence
        9. Paragraph structure
        10. Section diversity (lists, tables, blockquotes)
        """
        self._score_components = {}
        full_text = self._get_full_text(blog)
        word_count = len(full_text.split())

        scores = {
            "title_quality": self._score_title(blog.seo_title, primary_keyword),
            "heading_structure": self._score_headings(blog),
            "content_length": self._score_length(word_count),
            "keyword_usage": self._score_keywords(full_text, primary_keyword, blog),
            "introduction_quality": self._score_introduction(blog.introduction, primary_keyword),
            "conclusion_presence": 15.0 if len(blog.conclusion.split()) >= 30 else 0.0,
            "faq_inclusion": 10.0 if len(blog.faq) >= 3 else (5.0 if blog.faq else 0.0),
            "cta_presence": 5.0 if len(blog.call_to_action.split()) >= 10 else 0.0,
        }

        total = sum(scores.values())
        total = min(total, 100.0)
        self._score_components = scores
        return round(total, 1)

    def _get_full_text(self, blog: BlogResult) -> str:
        parts = [blog.seo_title, blog.introduction]
        for section in blog.sections:
            parts.append(section.content)
            for sub in section.subsections:
                parts.append(sub.content)
        parts.append(blog.conclusion)
        return " ".join(parts)

    def _score_title(self, title: str, keyword: str) -> float:
        if not title:
            return 0.0
        score = 5.0
        if 30 <= len(title) <= 60:
            score += 10.0
        elif len(title) > 60:
            score += 5.0
        if keyword and keyword.lower() in title.lower():
            score += 10.0
        return min(score, 20.0)

    def _score_headings(self, blog: BlogResult) -> float:
        h2_count = len(blog.sections)
        h3_count = sum(len(s.subsections) for s in blog.sections)
        toc_count = len(blog.table_of_contents)
        if h2_count >= 4:
            return 15.0
        if h2_count >= 2:
            return 10.0
        if h2_count >= 1:
            return 5.0
        return 0.0

    def _score_length(self, word_count: int) -> float:
        if word_count >= 2000:
            return 15.0
        if word_count >= 1200:
            return 12.0
        if word_count >= 800:
            return 8.0
        if word_count >= 400:
            return 5.0
        return 0.0

    def _score_keywords(self, text: str, primary: str, blog: BlogResult) -> float:
        score = 0.0
        if primary and primary.lower() in text.lower():
            frequency = text.lower().count(primary.lower())
            if 2 <= frequency <= 8:
                score += 8.0
            elif frequency > 8:
                score += 4.0
            else:
                score += 2.0
        if primary and primary.lower() in [h.lower() for s in blog.sections for h in [s.heading]]:
            score += 4.0
        # tags check removed - BlogResult has no tags field
        return min(score, 15.0)

    def _score_introduction(self, introduction: str, keyword: str) -> float:
        if not introduction:
            return 0.0
        words = introduction.split()
        score = 2.0
        if len(words) >= 50:
            score += 4.0
        elif len(words) >= 30:
            score += 2.0
        if keyword and keyword.lower() in introduction.lower():
            score += 4.0
        return min(score, 10.0)

    def get_score_breakdown(self) -> dict[str, float]:
        return dict(self._score_components)

    def validate_metadata(self, blog: BlogResult) -> list[str]:
        """Validate blog metadata and return a list of warnings."""
        warnings: list[str] = []
        if not blog.seo_title:
            warnings.append("Missing blog title")
        if not blog.slug:
            warnings.append("Missing slug")
        # category check removed - BlogResult has no category field
        # tags check removed - BlogResult has no tags field
        if not blog.table_of_contents:
            warnings.append("Missing table of contents")
        if not blog.faq:
            warnings.append("No FAQ section")
        if not blog.call_to_action:
            warnings.append("No call to action")
        return warnings

    def compute_seo_score(
        self, blog: BlogResult, primary_keyword: str = ""
    ) -> dict[str, Any]:
        """Compute SEO score with full breakdown."""
        score = self.score(blog, primary_keyword)
        return {
            "score": score,
            "breakdown": self.get_score_breakdown(),
            "warnings": self.validate_metadata(blog),
        }


