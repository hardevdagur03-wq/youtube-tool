"""Section Planner — enriches section plans with detailed metadata.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from outline_generator.outline_models import SectionPlan

logger = logging.getLogger(__name__)


class SectionPlanner:
    """Enriches generated section plans with facts, keywords, and structure."""

    def enrich(
        self,
        sections: list[SectionPlan],
        knowledge_graph: dict[str, Any] | None = None,
    ) -> list[SectionPlan]:
        kg = knowledge_graph or {}

        if not isinstance(kg, dict):
            return sections

        all_facts: list[str] = []
        facts = kg.get("facts", [])
        if isinstance(facts, list):
            all_facts = [str(f.get("statement", "")) for f in facts if isinstance(f, dict) and f.get("statement")]

        all_entities: list[str] = []
        entities = kg.get("entities", [])
        if isinstance(entities, list):
            all_entities = [str(e.get("name", "")) for e in entities if isinstance(e, dict) and e.get("name")]

        statistics: list[str] = []
        stats = kg.get("statistics", [])
        if isinstance(stats, list):
            statistics = [str(s.get("value", "")) + " " + str(s.get("unit", ""))
                          for s in stats if isinstance(s, dict) and s.get("value")]

        for i, section in enumerate(sections):
            if all_facts:
                section.supporting_facts = all_facts[i:i+2] if i < len(all_facts) else []
            if all_entities:
                section.entities = all_entities[i:i+3] if i < len(all_entities) else []
            if statistics:
                section.statistics = statistics[i:i+1] if i < len(statistics) else []

            if "example" in section.heading.lower() or "case" in section.heading.lower():
                section.examples = ["Real-world implementation example", "Industry case study"]

        return sections
