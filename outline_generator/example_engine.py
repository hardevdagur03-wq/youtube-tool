"""Example Engine — plans examples, use cases, and case studies.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from outline_generator.outline_models import ExamplePlan

logger = logging.getLogger(__name__)


class ExampleEngine:
    """Plans real-world examples, use cases, and case studies."""

    def plan(
        self,
        primary_keyword: str,
        knowledge_graph: dict[str, Any] | None = None,
        seo_plan: dict[str, Any] | None = None,
    ) -> list[ExamplePlan]:
        examples: list[ExamplePlan] = []
        kg = knowledge_graph or {}
        sp = seo_plan or {}

        depth = "comprehensive"
        if isinstance(sp, dict):
            cs = sp.get("content_strategy", {})
            if isinstance(cs, dict):
                depth = cs.get("content_depth", "comprehensive")

        examples.append(ExamplePlan(
            type="real_world",
            topic=f"Industry example of {primary_keyword} implementation",
            placement_section="overview",
            purpose=f"Show how {primary_keyword} is applied in real scenarios",
            priority=8,
        ))

        if depth in ("comprehensive", "ultimate"):
            examples.append(ExamplePlan(
                type="use_case",
                topic=f"Common use cases for {primary_keyword}",
                placement_section="applications",
                purpose=f"Demonstrate practical applications of {primary_keyword}",
                priority=7,
            ))

            examples.append(ExamplePlan(
                type="case_study",
                topic=f"Success story using {primary_keyword}",
                placement_section="case_studies",
                purpose="Provide evidence of effectiveness through real results",
                priority=8,
            ))

        has_code_entities = False
        if isinstance(kg, dict):
            entities = kg.get("entities", [])
            if isinstance(entities, list):
                has_code_entities = any(
                    isinstance(e, dict) and e.get("type") in ("language", "framework", "library")
                    for e in entities
                )

        if has_code_entities or depth == "ultimate":
            examples.append(ExamplePlan(
                type="code_example",
                topic=f"Code implementation of {primary_keyword}",
                placement_section="implementation",
                purpose="Provide hands-on code example for practical learning",
                priority=9,
            ))

        return examples
