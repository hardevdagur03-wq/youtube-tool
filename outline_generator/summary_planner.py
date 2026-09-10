"""Summary Planner — plans the conclusion and key takeaways.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from outline_generator.outline_models import SummaryPlan

logger = logging.getLogger(__name__)


class SummaryPlanner:
    """Plans the conclusion, takeaways, and action items."""

    def plan(
        self,
        primary_keyword: str,
        knowledge_graph: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
    ) -> SummaryPlan:
        plan = SummaryPlan()
        kg = knowledge_graph or {}
        analysis_data = analysis or {}

        plan.key_takeaways = [
            f"{primary_keyword} is a powerful tool for achieving better outcomes",
            f"Understanding the fundamentals of {primary_keyword} is essential for success",
            f"Practical implementation of {primary_keyword} leads to measurable improvements",
        ]

        if isinstance(kg, dict):
            facts = kg.get("facts", [])
            if isinstance(facts, list):
                for i, fact in enumerate(facts[:3]):
                    if isinstance(fact, dict):
                        statement = fact.get("statement", "")
                        if statement and len(statement) > 20:
                            plan.key_takeaways.append(statement[:150])

            pain_points = kg.get("pain_points", [])
            if isinstance(pain_points, list) and pain_points:
                plan.recap_points = [
                    f"We identified key challenges: {[p.get('problem', '') for p in pain_points[:3] if isinstance(p, dict)]}",
                    f"We provided solutions to overcome these obstacles",
                ]

        if isinstance(analysis_data, dict):
            takeaways = analysis_data.get("key_takeaways", [])
            if isinstance(takeaways, list):
                for t in takeaways:
                    t_str = str(t) if not isinstance(t, str) else t
                    if t_str not in plan.key_takeaways:
                        plan.key_takeaways.append(t_str)

        plan.final_thoughts = (f"{primary_keyword} continues to evolve and shape the industry. "
                               f"By staying informed and applying the best practices outlined in this guide, "
                               f"you can stay ahead of the curve.")
        plan.action_items = [
            f"Evaluate your current {primary_keyword} knowledge and identify gaps",
            f"Implement the strategies discussed in this guide",
            f"Monitor your progress and iterate on your approach",
        ]
        plan.closing_strategy = f"End with an encouraging message and final CTA about {primary_keyword}"
        plan.target_word_count = 150

        return plan
