"""Word Count Estimator — estimates word counts per section and total.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from outline_generator.outline_models import WordCountPlan, SectionPlan

logger = logging.getLogger(__name__)


class WordCountEstimator:
    """Estimates word counts for sections and total content."""

    def estimate(
        self,
        sections: list[SectionPlan],
        seo_plan: dict[str, Any] | None = None,
    ) -> WordCountPlan:
        plan = WordCountPlan()
        sp = seo_plan or {}

        depth = "comprehensive"
        recommended_wc = 2000
        if isinstance(sp, dict):
            cs = sp.get("content_strategy", {})
            if isinstance(cs, dict):
                depth = cs.get("content_depth", "comprehensive")
                recommended_wc = cs.get("recommended_word_count", 2000)

        if depth == "thin":
            plan.total_minimum = 600
            plan.total_target = 1000
            plan.total_maximum = 1500
        elif depth == "standard":
            plan.total_minimum = 1000
            plan.total_target = 1500
            plan.total_maximum = 2500
        elif depth == "comprehensive":
            plan.total_minimum = 1500
            plan.total_target = max(recommended_wc, 2000)
            plan.total_maximum = 4000
        else:
            plan.total_minimum = 2500
            plan.total_target = max(recommended_wc, 3500)
            plan.total_maximum = 6000

        plan.introduction = 150
        plan.body_per_section = max(200, plan.total_target // max(len(sections), 4))
        plan.conclusion = 150

        for section in sections:
            section_word_count = plan.body_per_section
            if section.has_code:
                section_word_count += 100
            if section.examples:
                section_word_count += 150 * len(section.examples)
            section.target_word_count = section_word_count
            plan.section_word_counts[section.heading] = section_word_count

        calculated_total = plan.introduction + sum(plan.section_word_counts.values()) + plan.conclusion
        if calculated_total < plan.total_target:
            scale = plan.total_target / max(calculated_total, 1)
            for heading in plan.section_word_counts:
                plan.section_word_counts[heading] = int(plan.section_word_counts[heading] * scale)
            plan.introduction = int(plan.introduction * scale)
            plan.conclusion = int(plan.conclusion * scale)

        return plan
