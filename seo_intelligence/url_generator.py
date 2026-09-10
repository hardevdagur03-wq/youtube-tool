"""URL Generator — creates SEO-friendly URLs from primary keyword.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
import re

from seo_intelligence.seo_models import URLInfo

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "up", "about", "into", "over", "after",
    "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "can", "could", "should",
    "may", "might", "shall", "not", "no", "nor", "so", "yet",
}


class URLGenerator:
    """Generates SEO-optimized URLs."""

    def generate(self, primary_keyword: str, title: str = "") -> URLInfo:
        info = URLInfo()

        source = primary_keyword or title or "blog-post"
        slug = source.lower()

        # Remove special chars
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"\s+", "-", slug.strip())

        # Remove stop words
        parts = slug.split("-")
        filtered = [p for p in parts if p not in STOP_WORDS or len(parts) <= 3]
        slug = "-".join(filtered) if filtered else slug

        # Limit length
        if len(slug) > 60:
            slug = "-".join(slug.split("-")[:8])
        if len(slug) > 80:
            slug = slug[:80].rstrip("-")

        if not slug:
            slug = "blog-post"

        info.suggested_slug = slug
        info.full_url = f"https://example.com/blog/{slug}"
        info.length = len(slug)
        info.keyword_included = primary_keyword.lower().replace(" ", "-") in slug
        info.readable_score = self._compute_readability(slug)

        return info

    @staticmethod
    def _compute_readability(slug: str) -> float:
        parts = slug.split("-")
        if len(parts) <= 1:
            return 0.5
        avg_len = sum(len(p) for p in parts) / len(parts)
        if 3 <= avg_len <= 8:
            return 0.9
        if 2 <= avg_len <= 10:
            return 0.7
        return 0.5
