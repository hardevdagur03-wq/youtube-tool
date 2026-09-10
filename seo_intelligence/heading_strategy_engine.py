"""Heading Strategy Engine — generates heading structure for content.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from seo_intelligence.seo_models import (
    HeadingStrategy, HeadingSuggestion, ContentStrategy, ContentDepth,
)

logger = logging.getLogger(__name__)

DEFAULT_H2_TEMPLATES = [
    "What is {keyword}?",
    "Why {keyword} Matters",
    "Key Benefits of {keyword}",
    "How to Get Started with {keyword}",
    "Best Practices for {keyword}",
    "Common Challenges with {keyword}",
    "{keyword} vs Alternatives",
    "Advanced {keyword} Techniques",
    "Case Studies: {keyword} in Action",
    "Future of {keyword}",
    "Frequently Asked Questions About {keyword}",
    "Conclusion",
]

DEFAULT_H3_TEMPLATES = [
    "Understanding the Basics",
    "Step-by-Step Implementation",
    "Expert Tips and Tricks",
    "Common Mistakes to Avoid",
    "Tools and Resources",
    "Measuring Success",
]


class HeadingStrategyEngine:
    """Generates heading structure optimized for target keywords."""

    def generate(
        self,
        primary_keyword: str,
        secondary_keywords: list[str],
        knowledge_graph: dict[str, Any] | None,
    ) -> tuple[HeadingStrategy, ContentStrategy]:
        strategy = HeadingStrategy()
        content = ContentStrategy()
        used_texts: set[str] = set()

        strategy.h1 = primary_keyword or "Comprehensive Guide"

        depth = ContentDepth.COMPREHENSIVE
        keyword_count = len(secondary_keywords)
        if keyword_count < 5:
            depth = ContentDepth.STANDARD
        elif keyword_count < 10:
            depth = ContentDepth.COMPREHENSIVE
        else:
            depth = ContentDepth.ULTIMATE
        content.content_depth = depth

        # Determine how many headings based on depth
        h2_count = {"standard": 5, "comprehensive": 8, "ultimate": 12, "thin": 3}.get(depth.value, 8)
        h3_count = max(2, h2_count // 2)

        # Generate H2s
        for i in range(h2_count):
            template = DEFAULT_H2_TEMPLATES[i % len(DEFAULT_H2_TEMPLATES)]
            kw = secondary_keywords[i % max(1, len(secondary_keywords))] if secondary_keywords else primary_keyword
            text = template.format(keyword=kw if i > 0 else primary_keyword)

            if text.lower() not in used_texts:
                used_texts.add(text.lower())
                kw_included = kw.lower() in text.lower() or primary_keyword.lower() in text.lower()
                strategy.h2_suggestions.append(HeadingSuggestion(
                    tag="h2",
                    text=text,
                    keyword_included=kw_included,
                    related_keywords=[kw] if kw != primary_keyword else [],
                    order=i + 1,
                ))

        # Generate H3s
        for i in range(h3_count):
            template = DEFAULT_H3_TEMPLATES[i % len(DEFAULT_H3_TEMPLATES)]
            text = template

            if text.lower() not in used_texts:
                used_texts.add(text.lower())
                strategy.h3_suggestions.append(HeadingSuggestion(
                    tag="h3",
                    text=text,
                    keyword_included=False,
                    order=i + 1,
                ))

        strategy.total_headings = 1 + len(strategy.h2_suggestions) + len(strategy.h3_suggestions)
        kw_hits = sum(1 for h in strategy.h2_suggestions if h.keyword_included)
        strategy.keyword_coverage = kw_hits / max(len(strategy.h2_suggestions), 1)

        # Content depth recommendations
        word_counts = {"thin": 800, "standard": 1500, "comprehensive": 2500, "ultimate": 4000}
        content.recommended_word_count = word_counts.get(depth.value, 1500)
        content.recommended_headings = strategy.total_headings
        content.recommended_images = max(2, h2_count // 2)
        content.recommended_examples = max(2, h2_count // 3)
        content.recommended_statistics = max(1, h2_count // 4)
        content.recommended_quotes = max(1, h2_count // 4)

        if depth == ContentDepth.ULTIMATE:
            content.recommended_tables = 2
            content.recommended_case_studies = 2

        return strategy, content
