"""Internal Link Engine — suggests internal linking opportunities.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from seo_intelligence.seo_models import InternalLink

logger = logging.getLogger(__name__)


class InternalLinkEngine:
    """Generates internal linking suggestions from knowledge graph entities."""

    def generate(
        self,
        knowledge_graph: dict[str, Any] | None,
        primary_keyword: str = "",
    ) -> list[InternalLink]:
        links: list[InternalLink] = []
        seen: set[str] = set()
        kg = knowledge_graph or {}

        if not isinstance(kg, dict):
            return links

        clusters = kg.get("semantic_clusters", [])
        if isinstance(clusters, list):
            for cluster in clusters:
                if isinstance(cluster, dict):
                    name = cluster.get("name", "")
                    entities = cluster.get("entities", [])
                    if isinstance(entities, list):
                        for entity in entities[:3]:
                            if isinstance(entity, str) and entity.lower() not in seen:
                                seen.add(entity.lower())
                                links.append(InternalLink(
                                    target_topic=entity,
                                    suggested_anchor=f"Learn more about {entity}",
                                    relevance_score=0.6,
                                    priority=6,
                                    placement_suggestion=f"natural {name} context",
                                ))

        entities = kg.get("entities", [])
        if isinstance(entities, list):
            for entity in entities[:5]:
                if isinstance(entity, dict):
                    name = entity.get("name", "")
                    if name and name.lower() not in seen and name != primary_keyword:
                        seen.add(name.lower())
                        links.append(InternalLink(
                            target_topic=name,
                            suggested_anchor=f"Read about {name}",
                            relevance_score=entity.get("importance_score", 0.5),
                            priority=int(entity.get("importance_score", 0.5) * 10),
                            placement_suggestion="related context section",
                        ))

        if primary_keyword:
            links.append(InternalLink(
                target_topic=primary_keyword,
                suggested_anchor=f"Comprehensive guide to {primary_keyword}",
                relevance_score=1.0,
                priority=10,
                placement_suggestion="introduction or summary section",
            ))

        return links
