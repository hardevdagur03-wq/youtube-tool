"""FAQ Planner — plans FAQ placement and structure for the outline.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from outline_generator.outline_models import FAQPlan

logger = logging.getLogger(__name__)


class FAQPlanner:
    """Plans FAQs for the content outline from SEO plan and knowledge graph."""

    def plan(
        self,
        primary_keyword: str,
        seo_plan: dict[str, Any] | None = None,
        knowledge_graph: dict[str, Any] | None = None,
    ) -> list[FAQPlan]:
        faqs: list[FAQPlan] = []
        seen: set[str] = set()
        sp = seo_plan or {}
        kg = knowledge_graph or {}

        if isinstance(sp, dict):
            faq_items = sp.get("faqs", [])
            if isinstance(faq_items, list):
                for item in faq_items:
                    if isinstance(item, dict):
                        q = item.get("question", "")
                        if q and q.lower() not in seen:
                            seen.add(q.lower())
                            faqs.append(FAQPlan(
                                question=q,
                                answer_summary="",
                                intent=item.get("intent", "informational"),
                                recommended_answer_length=100,
                                priority=item.get("priority", 5),
                                placement_section="faq",
                            ))

        if isinstance(kg, dict):
            definitions = kg.get("definitions", [])
            if isinstance(definitions, list):
                for d in definitions:
                    if isinstance(d, dict):
                        term = d.get("term", "")
                        if term:
                            q = f"What is {term}?"
                            if q.lower() not in seen:
                                seen.add(q.lower())
                                faqs.append(FAQPlan(
                                    question=q,
                                    answer_summary=d.get("definition", "")[:100],
                                    intent="informational",
                                    recommended_answer_length=80,
                                    priority=6,
                                    placement_section="faq",
                                ))

        base_questions = [
            f"What is {primary_keyword}?",
            f"Why is {primary_keyword} important?",
            f"How does {primary_keyword} work?",
            f"What are the benefits of {primary_keyword}?",
            f"How to get started with {primary_keyword}?",
        ]
        for q in base_questions:
            if q.lower() not in seen:
                seen.add(q.lower())
                faqs.append(FAQPlan(
                    question=q,
                    intent="informational",
                    recommended_answer_length=100,
                    priority=5,
                    placement_section="faq",
                ))

        return faqs
