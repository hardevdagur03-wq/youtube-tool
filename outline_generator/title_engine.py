"""Title Engine — generates primary, SEO, and alternative titles.

Consumes seo_plan.json and analysis.json. No external API calls.
No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from outline_generator.outline_models import TitleInfo

logger = logging.getLogger(__name__)

TITLE_TEMPLATES = [
    "{keyword}: The Complete Guide for {audience}",
    "{keyword}: A Comprehensive Overview",
    "The Ultimate Guide to {keyword}",
    "{keyword} Explained: Everything You Need to Know",
    "Mastering {keyword}: Tips, Tricks, and Best Practices",
    "{keyword}: From Basics to Advanced Techniques",
    "What Is {keyword}? A Practical Introduction",
    "{keyword} for {audience}: Getting Started Guide",
]


class TitleEngine:
    """Generates primary, SEO-optimized, and alternative titles."""

    def generate(
        self,
        primary_keyword: str,
        seo_plan: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
    ) -> TitleInfo:
        info = TitleInfo()
        analysis_data = analysis or {}
        sp = seo_plan or {}

        audience = "Beginners"
        if isinstance(analysis_data, dict):
            raw = analysis_data.get("target_audience", "")
            if isinstance(raw, str) and raw:
                audience = raw
            elif isinstance(sp, dict):
                ta = sp.get("target_audience", {})
                if isinstance(ta, dict):
                    audience = ta.get("primary_audience", "Beginners")

        if not primary_keyword:
            if isinstance(analysis_data, dict):
                primary_keyword = analysis_data.get("primary_topic", "") or analysis_data.get("title", "")
            if not primary_keyword:
                primary_keyword = "Blog Post"

        info.primary_title = f"{primary_keyword}: A Comprehensive Guide"
        info.seo_title = f"{primary_keyword}: Complete Guide & Best Practices"
        info.ctr_title = f"{primary_keyword}: The Ultimate Guide for {audience}"

        seen = {info.primary_title.lower(), info.seo_title.lower(), info.ctr_title.lower()}
        for template in TITLE_TEMPLATES:
            title = template.format(keyword=primary_keyword, audience=audience)
            if title.lower() not in seen and len(info.alternative_titles) < 5:
                seen.add(title.lower())
                info.alternative_titles.append(title)

        info.length = len(info.primary_title)
        info.pixel_width = info.length * 8
        info.seo_score = 0.7 if info.length < 60 else 0.4
        info.ctr_score = 0.8 if "Ultimate" in info.ctr_title or "Complete" in info.ctr_title else 0.5
        info.keyword_coverage = 1.0 if primary_keyword.lower() in info.primary_title.lower() else 0.0

        return info
