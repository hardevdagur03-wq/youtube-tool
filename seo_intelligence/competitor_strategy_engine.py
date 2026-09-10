"""Competitor Strategy Engine — analyzes content differentiation opportunities.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from seo_intelligence.seo_models import CompetitorStrategy

logger = logging.getLogger(__name__)


class CompetitorStrategyEngine:
    """Generates competitive differentiation strategy from knowledge graph."""

    def generate(
        self,
        primary_keyword: str = "",
        knowledge_graph: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
    ) -> CompetitorStrategy:
        strategy = CompetitorStrategy()
        kg = knowledge_graph or {}
        analysis_data = analysis or {}

        if primary_keyword:
            if isinstance(analysis_data, dict):
                content_type = analysis_data.get("content_type", "")
                if isinstance(content_type, str) and content_type:
                    strategy.content_angle = f"Comprehensive {content_type.lower()} covering {primary_keyword}"
                else:
                    strategy.content_angle = f"In-depth analysis of {primary_keyword}"

        if isinstance(kg, dict):
            clusters = kg.get("semantic_clusters", [])
            if isinstance(clusters, list):
                for cluster in clusters:
                    if isinstance(cluster, dict):
                        entities = cluster.get("entities", [])
                        if isinstance(entities, list) and len(entities) > 2:
                            strategy.missing_topics.append(
                                f"Cover all entities in {cluster.get('name', 'topic')} cluster"
                            )

            pain_points = kg.get("pain_points", [])
            if isinstance(pain_points, list) and pain_points:
                strategy.content_gaps.append("Address identified pain points comprehensively")

            solutions = kg.get("solutions", [])
            if isinstance(solutions, list) and solutions:
                strategy.competitive_advantages.append("Provide detailed solutions for each pain point")

            entities = kg.get("entities", [])
            if isinstance(entities, list):
                entity_count = len(entities)
                if entity_count > 5:
                    strategy.authority_opportunities.append(
                        f"Covers {entity_count} unique entities for topical authority"
                    )
                if entity_count > 3:
                    strategy.competitive_advantages.append(
                        f"Wealth of entity coverage ({entity_count} entities)"
                    )

        if isinstance(analysis_data, dict):
            keywords = analysis_data.get("keywords", {})
            if isinstance(keywords, dict):
                long_tail = keywords.get("long_tail", [])
                if isinstance(long_tail, list) and long_tail:
                    strategy.authority_opportunities.append(
                        f"Target {len(long_tail)} long-tail keyword opportunities"
                    )

        strategy.unique_value_proposition = (
            f"Comprehensive, data-driven exploration of {primary_keyword} "
            f"with practical insights and expert analysis"
        )
        strategy.differentiation_notes = (
            f"Leverage unique entity and relationship data from the knowledge graph "
            f"to provide deeper insights than typical blog posts on {primary_keyword}"
        )

        return strategy
