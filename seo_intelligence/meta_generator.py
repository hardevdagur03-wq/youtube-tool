"""Meta Generator — creates SEO meta titles, descriptions, and Open Graph tags.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from seo_intelligence.seo_models import MetaInfo, SearchIntentType

logger = logging.getLogger(__name__)

TITLE_TEMPLATES = {
    SearchIntentType.INFORMATIONAL: "{keyword}: Complete Guide {year}",
    SearchIntentType.EDUCATIONAL: "{keyword}: Learn {topic} Step by Step",
    SearchIntentType.TUTORIAL: "{keyword} Tutorial: A Practical Guide",
    SearchIntentType.COMMERCIAL: "Best {keyword} in {year}: Top Picks & Reviews",
    SearchIntentType.COMPARISON: "{keyword} vs {alternative}: Which is Better?",
    SearchIntentType.REVIEW: "{keyword} Review: Pros, Cons & Verdict",
    SearchIntentType.TRANSACTIONAL: "Buy {keyword} Online | Best Deals {year}",
    SearchIntentType.NAVIGATIONAL: "{keyword} - Official Guide & Resources",
}

DESCRIPTION_TEMPLATES = {
    SearchIntentType.INFORMATIONAL: "Learn everything about {keyword} in this comprehensive guide. Discover {key_benefit} and master {topic} with our expert tips.",
    SearchIntentType.EDUCATIONAL: "Master {keyword} with this step-by-step guide. Perfect for {audience}. Start learning today!",
    SearchIntentType.TUTORIAL: "Follow our step-by-step {keyword} tutorial. {key_benefit} with practical examples and expert advice.",
    SearchIntentType.COMMERCIAL: "Looking for the best {keyword}? Compare top {keyword} options, read expert reviews, and find the perfect solution for {audience}.",
}


class MetaGenerator:
    """Generates meta titles, descriptions, and social tags."""

    def generate(
        self,
        primary_keyword: str,
        search_intent: SearchIntentType,
        audience: str = "",
        analysis: dict[str, Any] | None = None,
    ) -> MetaInfo:
        meta = MetaInfo()
        analysis_data = analysis or {}
        now = __import__("datetime").datetime.now()

        topic = primary_keyword or ""
        alternative = "Alternatives"
        key_benefit = "unlock new opportunities"
        year = str(now.year)

        if isinstance(analysis_data, dict):
            secondary = analysis_data.get("secondary_topics", [])
            if isinstance(secondary, list) and secondary:
                alternative = str(secondary[0])
            summary = analysis_data.get("summary", {})
            if isinstance(summary, dict):
                short = summary.get("short", "")
                if isinstance(short, str) and short:
                    key_benefit = short[:80]

        # Meta title
        template = TITLE_TEMPLATES.get(search_intent, TITLE_TEMPLATES[SearchIntentType.INFORMATIONAL])
        meta_title = template.format(
            keyword=primary_keyword or topic,
            topic=topic,
            alternative=alternative,
            year=year,
        )
        if len(meta_title) > 60:
            meta_title = meta_title[:57] + "..."
        meta.meta_title = meta_title
        meta.meta_title_length = len(meta_title)
        meta.meta_title_pixels = len(meta_title) * 8
        meta.meta_title_ctr_score = 0.6 if len(meta_title) < 55 else 0.4

        # Meta description
        desc_template = DESCRIPTION_TEMPLATES.get(
            search_intent, DESCRIPTION_TEMPLATES[SearchIntentType.INFORMATIONAL]
        )
        meta_desc = desc_template.format(
            keyword=primary_keyword or topic,
            topic=topic,
            key_benefit=key_benefit,
            audience=audience or "everyone",
            year=year,
        )
        if len(meta_desc) > 160:
            meta_desc = meta_desc[:157] + "..."
        meta.meta_description = meta_desc
        meta.meta_description_length = len(meta_desc)
        meta.meta_description_ctr_score = 0.6 if 120 <= len(meta_desc) <= 160 else 0.4

        # Open Graph
        meta.og_title = meta_title
        meta.og_description = meta_desc
        meta.og_image_alt = primary_keyword or "Blog post image"

        # Twitter
        meta.twitter_title = meta_title
        meta.twitter_description = meta_desc

        return meta
