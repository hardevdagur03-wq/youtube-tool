"""Entity Extractor — extracts structured entities from existing analysis output.

Consumes analysis.json. No external API calls.
No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from knowledge_graph.knowledge_graph_models import (
    EntityInfo,
    EntityType,
    Confidence,
    Importance,
)

logger = logging.getLogger(__name__)

TYPE_MAP: dict[str, EntityType] = {
    "people": EntityType.PERSON,
    "persons": EntityType.PERSON,
    "companies": EntityType.COMPANY,
    "organizations": EntityType.ORGANIZATION,
    "universities": EntityType.ORGANIZATION,
    "countries": EntityType.LOCATION,
    "cities": EntityType.LOCATION,
    "locations": EntityType.LOCATION,
    "technologies": EntityType.TECHNOLOGY,
    "programming_languages": EntityType.LANGUAGE,
    "frameworks": EntityType.FRAMEWORK,
    "libraries": EntityType.LIBRARY,
    "tools": EntityType.TOOL,
    "products": EntityType.PRODUCT,
    "books": EntityType.BOOK,
    "courses": EntityType.EVENT,
    "apis": EntityType.API,
    "platforms": EntityType.PLATFORM,
    "standards": EntityType.STANDARD,
    "research_papers": EntityType.RESEARCH_PAPER,
    "events": EntityType.EVENT,
    "concepts": EntityType.CONCEPT,
}


class EntityExtractor:
    """Extracts structured entities from existing analysis output."""

    def extract(self, analysis: dict[str, Any]) -> list[EntityInfo]:
        entities: list[EntityInfo] = []
        seen: set[str] = set()
        entities_data = analysis.get("entities", {}) if analysis else {}

        if not isinstance(entities_data, dict):
            return entities

        for category, names in entities_data.items():
            entity_type = TYPE_MAP.get(category.lower(), EntityType.OTHER)
            if isinstance(names, list):
                for i, name in enumerate(names):
                    if isinstance(name, str) and name.lower() not in seen:
                        seen.add(name.lower())
                        entities.append(EntityInfo(
                            name=name,
                            type=entity_type,
                            frequency=names.count(name),
                            importance_score=1.0 - (i / max(len(names), 1) * 0.5),
                            confidence=Confidence.HIGH,
                            mentions=[name],
                        ))

        if analysis:
            topic_name = ""
            if isinstance(analysis, dict):
                topic_name = analysis.get("primary_topic", "") or analysis.get("title", "")
            if topic_name and topic_name.lower() not in seen:
                entities.append(EntityInfo(
                    name=topic_name,
                    type=EntityType.CONCEPT,
                    importance_score=1.0,
                    confidence=Confidence.HIGH,
                ))

        return entities
