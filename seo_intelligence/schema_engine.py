"""Schema Engine — generates JSON-LD schema markup recommendations.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from seo_intelligence.seo_models import SchemaMarkup, SchemaType

logger = logging.getLogger(__name__)


class SchemaEngine:
    """Generates schema.org JSON-LD markup recommendations."""

    def generate(
        self,
        primary_keyword: str = "",
        meta_title: str = "",
        meta_description: str = "",
        analysis: dict[str, Any] | None = None,
    ) -> list[SchemaMarkup]:
        schemas: list[SchemaMarkup] = []
        analysis_data = analysis or {}

        # Article schema (always)
        article = SchemaMarkup(
            type=SchemaType.ARTICLE,
            priority=10,
            notes="Core article schema for all blog content",
            template={
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": meta_title or primary_keyword or "Blog Post",
                "description": meta_description or "",
            },
        )
        article.json_ld = json.dumps(article.template, indent=2)
        schemas.append(article)

        # FAQ schema (if we can generate FAQs)
        faq = SchemaMarkup(
            type=SchemaType.FAQ,
            priority=8,
            notes="FAQ schema enables rich results in search",
            template={
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [],
            },
        )
        faq.json_ld = json.dumps(faq.template, indent=2)
        schemas.append(faq)

        # Video schema (since content is from YouTube)
        video = SchemaMarkup(
            type=SchemaType.VIDEO,
            priority=7,
            notes="Video schema since content originates from YouTube",
            template={
                "@context": "https://schema.org",
                "@type": "VideoObject",
                "name": primary_keyword or "YouTube Video Content",
                "description": meta_description or "",
            },
        )
        video.json_ld = json.dumps(video.template, indent=2)
        schemas.append(video)

        # Breadcrumb schema
        breadcrumb = SchemaMarkup(
            type=SchemaType.BREADCRUMB,
            priority=6,
            notes="Breadcrumb helps navigation and rich results",
            template={
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://example.com/"},
                    {"@type": "ListItem", "position": 2, "name": "Blog", "item": "https://example.com/blog/"},
                    {"@type": "ListItem", "position": 3, "name": primary_keyword or "Article"},
                ],
            },
        )
        breadcrumb.json_ld = json.dumps(breadcrumb.template, indent=2)
        schemas.append(breadcrumb)

        # HowTo schema if tutorial intent
        if isinstance(analysis_data, dict):
            intent = analysis_data.get("search_intent", "")
            if isinstance(intent, str) and intent.lower() in ("tutorial", "how_to"):
                howto = SchemaMarkup(
                    type=SchemaType.HOW_TO,
                    priority=7,
                    notes="HowTo schema for tutorial content",
                    template={
                        "@context": "https://schema.org",
                        "@type": "HowTo",
                        "name": meta_title or primary_keyword or "How To Guide",
                        "description": meta_description or "",
                        "step": [],
                    },
                )
                howto.json_ld = json.dumps(howto.template, indent=2)
                schemas.append(howto)

        return schemas
