"""Heading Generator — generates heading hierarchy from SEO plan and knowledge graph.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from outline_generator.outline_models import SectionPlan

logger = logging.getLogger(__name__)

BASE_H2_TEMPLATES = [
    "What is {keyword}?",
    "Why {keyword} Matters",
    "Key Benefits of {keyword}",
    "How {keyword} Works",
    "Getting Started with {keyword}",
    "Core Concepts of {keyword}",
    "Advanced {keyword} Techniques",
    "Best Practices for {keyword}",
    "Common Challenges with {keyword}",
    "{keyword} vs Alternatives",
    "Tools and Resources for {keyword}",
    "Real-World Applications of {keyword}",
    "Case Studies: {keyword} in Action",
    "Expert Tips for {keyword}",
    "Future of {keyword}",
    "Frequently Asked Questions About {keyword}",
]

H3_TOPICS = [
    "Understanding the Fundamentals",
    "Step-by-Step Implementation Guide",
    "Common Mistakes to Avoid",
    "Performance Optimization Tips",
    "Security Considerations",
    "Integration with Other Systems",
    "Testing and Validation",
    "Deployment Strategies",
    "Monitoring and Analytics",
    "Scaling Considerations",
]


class HeadingGenerator:
    """Generates a logical heading hierarchy from existing data."""

    def generate(
        self,
        primary_keyword: str,
        secondary_keywords: list[str],
        knowledge_graph: dict[str, Any] | None = None,
        seo_plan: dict[str, Any] | None = None,
    ) -> list[SectionPlan]:
        sections: list[SectionPlan] = []
        used_headings: set[str] = set()
        kg = knowledge_graph or {}
        sp = seo_plan or {}

        # Adjust count based on content depth
        depth = "comprehensive"
        if isinstance(sp, dict):
            cs = sp.get("content_strategy", {})
            if isinstance(cs, dict):
                depth = cs.get("content_depth", "comprehensive")

        h2_count = {"thin": 4, "standard": 7, "comprehensive": 10, "ultimate": 14}.get(depth, 10)

        # Determine facts and entities from KG
        kg_facts: list[str] = []
        kg_entities: list[str] = []
        if isinstance(kg, dict):
            facts = kg.get("facts", [])
            if isinstance(facts, list):
                kg_facts = [str(f.get("statement", "")) for f in facts if isinstance(f, dict) and f.get("statement")]
            entities = kg.get("entities", [])
            if isinstance(entities, list):
                kg_entities = [str(e.get("name", "")) for e in entities if isinstance(e, dict) and e.get("name")]

        for i in range(h2_count):
            template_idx = i % len(BASE_H2_TEMPLATES)
            template = BASE_H2_TEMPLATES[template_idx]

            kw = primary_keyword
            if i > 0 and secondary_keywords:
                kw = secondary_keywords[i % len(secondary_keywords)]

            heading = template.format(keyword=kw)
            if heading.lower() in used_headings:
                heading = template.format(keyword=primary_keyword)
                if heading.lower() in used_headings:
                    continue
            used_headings.add(heading.lower())

            # Determine supporting data for this section
            section_facts = kg_facts[i:i+2] if i < len(kg_facts) else []
            section_entities = kg_entities[i:i+3] if i < len(kg_entities) else []

            goal_map = {
                0: f"Define and introduce {primary_keyword}",
                1: f"Explain the importance and relevance of {primary_keyword}",
                2: f"List and describe the key benefits",
                3: f"Explain how {primary_keyword} works",
                4: f"Guide the reader through initial steps",
                5: f"Cover fundamental concepts and principles",
                6: f"Dive into advanced techniques",
                7: f"Share established best practices",
                8: f"Address common obstacles and solutions",
                9: f"Compare {primary_keyword} with alternatives",
            }

            section = SectionPlan(
                heading=heading,
                heading_tag="h2",
                goal=goal_map.get(i, f"Explore {heading.lower()}"),
                summary=f"This section covers {heading.lower()}",
                supporting_facts=section_facts,
                entities=section_entities,
                keywords=[kw],
                target_word_count=300,
                priority=10 - i,
                order=i + 1,
                has_code=kw.lower() in ("code", "implementation", "programming"),
            )
            sections.append(section)

        return sections
