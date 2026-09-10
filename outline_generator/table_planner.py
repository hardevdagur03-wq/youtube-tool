"""Table Planner — recommends tables for the content outline.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from outline_generator.outline_models import TableRecommendation

logger = logging.getLogger(__name__)


class TablePlanner:
    """Recommends tables based on SEO plan and knowledge graph data."""

    def recommend(
        self,
        primary_keyword: str,
        secondary_keywords: list[str],
        seo_plan: dict[str, Any] | None = None,
    ) -> list[TableRecommendation]:
        tables: list[TableRecommendation] = []
        sp = seo_plan or {}

        depth = "comprehensive"
        if isinstance(sp, dict):
            cs = sp.get("content_strategy", {})
            if isinstance(cs, dict):
                depth = cs.get("content_depth", "comprehensive")

        tables.append(TableRecommendation(
            title=f"Comparison of {primary_keyword} Features",
            columns=["Feature", "Description", "Benefit"],
            purpose="Help readers compare different aspects at a glance",
            placement_section="overview",
            row_count=5,
            priority=8,
        ))

        if secondary_keywords and depth in ("comprehensive", "ultimate"):
            tables.append(TableRecommendation(
                title=f"{primary_keyword} vs {secondary_keywords[0]}: Key Differences",
                columns=["Aspect", primary_keyword, secondary_keywords[0]],
                purpose="Side-by-side comparison for decision making",
                placement_section="comparison",
                row_count=6,
                priority=7,
            ))

        if depth == "ultimate":
            tables.append(TableRecommendation(
                title=f"{primary_keyword}: Pros and Cons",
                columns=["Pros", "Cons"],
                purpose="Balanced evaluation of advantages and disadvantages",
                placement_section="evaluation",
                row_count=5,
                priority=6,
            ))

            tables.append(TableRecommendation(
                title=f"Quick Reference: {primary_keyword} Checklist",
                columns=["Task", "Difficulty", "Time Estimate"],
                purpose="Actionable checklist for readers",
                placement_section="getting_started",
                row_count=8,
                priority=7,
            ))

        return tables
