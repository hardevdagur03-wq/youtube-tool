"""Relationship Engine — identifies semantic relationships between entities.

Builds a graph of entity-to-entity, entity-to-topic, and concept-to-concept links.
No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from knowledge_graph.knowledge_graph_models import (
    EntityInfo,
    Relationship,
    RelationshipType,
    Confidence,
)

logger = logging.getLogger(__name__)


class RelationshipEngine:
    """Builds semantic relationships between entities in the knowledge graph."""

    def build(
        self,
        entities: list[EntityInfo],
        analysis: dict[str, Any] | None,
    ) -> list[Relationship]:
        relationships: list[Relationship] = []
        seen: set[tuple[str, str, str]] = set()

        # Cross-reference entities that appear in each other's related_entities
        for entity in entities:
            for related in entity.related_entities:
                key = (entity.name.lower(), related.lower(), "related_to")
                rev_key = (related.lower(), entity.name.lower(), "related_to")
                if key not in seen and rev_key not in seen:
                    seen.add(key)
                    relationships.append(Relationship(
                        source=entity.name,
                        target=related,
                        type=RelationshipType.RELATED_TO,
                        weight=0.5,
                        confidence=Confidence.MEDIUM,
                    ))

        # Topic-to-entity relationships from analysis
        if analysis and isinstance(analysis, dict):
            topic = analysis.get("primary_topic", "") or analysis.get("title", "")
            if topic:
                for entity in entities[:20]:
                    key = (topic.lower(), entity.name.lower(), "related_to")
                    rev_key = (entity.name.lower(), topic.lower(), "related_to")
                    if key not in seen and rev_key not in seen:
                        seen.add(key)
                        relationships.append(Relationship(
                            source=topic,
                            target=entity.name,
                            weight=0.8 - (entities.index(entity) * 0.02),
                            confidence=Confidence.HIGH,
                        ))

            secondary_topics = analysis.get("secondary_topics", [])
            if isinstance(secondary_topics, list):
                for st in secondary_topics[:10]:
                    if isinstance(st, str) and topic:
                        key = (topic.lower(), st.lower(), "related_to")
                        if key not in seen:
                            seen.add(key)
                            relationships.append(Relationship(
                                source=topic,
                                target=st,
                                type=RelationshipType.RELATED_TO,
                                weight=0.6,
                                confidence=Confidence.MEDIUM,
                            ))

            keywords = analysis.get("keywords", {})
            if isinstance(keywords, dict):
                primary = keywords.get("primary", [])
                if isinstance(primary, list) and primary:
                    pk = primary[0] if isinstance(primary[0], str) else ""
                    if pk and topic:
                        key = (topic.lower(), pk.lower(), "related_to")
                        if key not in seen:
                            seen.add(key)
                            relationships.append(Relationship(
                                source=topic,
                                target=pk,
                                weight=0.9,
                                confidence=Confidence.HIGH,
                            ))

        return relationships
