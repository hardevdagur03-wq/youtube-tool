"""SEO Validator — validates SEO plan quality and completeness.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from seo_intelligence.seo_models import SEOPlan

logger = logging.getLogger(__name__)


class SEOValidator:
    """Validates SEO plan completeness and quality."""

    def validate(self, plan: SEOPlan) -> list[str]:
        issues: list[str] = []

        if not plan.keyword_strategy.primary_keyword:
            issues.append("No primary keyword defined")

        if len(plan.keyword_strategy.secondary_keywords) < 3:
            issues.append(f"Only {len(plan.keyword_strategy.secondary_keywords)} secondary keywords (minimum 3)")

        if not plan.url.suggested_slug:
            issues.append("No URL slug generated")

        if not plan.meta.meta_title:
            issues.append("No meta title generated")
        elif len(plan.meta.meta_title) > 60:
            issues.append(f"Meta title too long: {len(plan.meta.meta_title)} chars (max 60)")

        if not plan.meta.meta_description:
            issues.append("No meta description generated")
        elif len(plan.meta.meta_description) > 160:
            issues.append(f"Meta description too long: {len(plan.meta.meta_description)} chars (max 160)")
        elif len(plan.meta.meta_description) < 120:
            issues.append(f"Meta description too short: {len(plan.meta.meta_description)} chars (min 120)")

        if not plan.heading_strategy.h1:
            issues.append("No H1 heading defined")
        if len(plan.heading_strategy.h2_suggestions) < 3:
            issues.append(f"Only {len(plan.heading_strategy.h2_suggestions)} H2 suggestions (minimum 3)")

        if not plan.schemas:
            issues.append("No schema markup defined")

        if len(plan.faqs) < 2:
            issues.append(f"Only {len(plan.faqs)} FAQ items (recommend at least 2)")

        if plan.content_strategy.recommended_word_count < 800:
            issues.append(f"Content too thin: {plan.content_strategy.recommended_word_count} words")

        seen_keywords: set[str] = set()
        for kw in plan.keyword_strategy.secondary_keywords:
            kw_lower = kw.keyword.lower()
            if kw_lower in seen_keywords:
                issues.append(f"Duplicate keyword: {kw.keyword}")
            seen_keywords.add(kw_lower)

        if plan.keyword_strategy.primary_keyword:
            pk_lower = plan.keyword_strategy.primary_keyword.lower()
            secondary_kws = [sk.keyword.lower() for sk in plan.keyword_strategy.secondary_keywords]
            if pk_lower in secondary_kws:
                issues.append("Primary keyword also appears in secondary keywords")

        return issues
