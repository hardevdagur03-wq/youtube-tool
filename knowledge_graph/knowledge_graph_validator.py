"""Knowledge Graph Validator — validates graph quality, detects duplicates, checks schema.

No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from knowledge_graph.knowledge_graph_models import KnowledgeGraph

logger = logging.getLogger(__name__)

MIN_ENTITIES = 1
MIN_KEYWORDS = 1
MAX_DUPLICATE_RATIO = 0.3


class KnowledgeGraphValidator:
    """Validates knowledge graph completeness, consistency, and quality."""

    def validate(self, kg: KnowledgeGraph) -> list[str]:
        issues: list[str] = []

        if kg.entity_count() < MIN_ENTITIES:
            issues.append(f"Too few entities: {kg.entity_count()} < {MIN_ENTITIES}")

        if kg.keyword_count() < MIN_KEYWORDS:
            issues.append(f"Too few keywords: {kg.keyword_count()} < {MIN_KEYWORDS}")

        seen_entities: set[str] = set()
        for entity in kg.entities:
            name_lower = entity.name.lower()
            if name_lower in seen_entities:
                issues.append(f"Duplicate entity: {entity.name}")
            seen_entities.add(name_lower)

        seen_keywords: set[str] = set()
        for kw in kg.keywords:
            kw_lower = kw.keyword.lower()
            if kw_lower in seen_keywords:
                issues.append(f"Duplicate keyword: {kw.keyword}")
            seen_keywords.add(kw_lower)

        seen_facts: set[str] = set()
        for fact in kg.facts:
            fact_lower = fact.statement[:50].lower()
            if fact_lower in seen_facts:
                issues.append(f"Near-duplicate fact: {fact.statement[:80]}...")
            seen_facts.add(fact_lower)

        seen_relationships: set[tuple[str, str]] = set()
        for rel in kg.relationships:
            key = (rel.source.lower(), rel.target.lower())
            rev_key = (rel.target.lower(), rel.source.lower())
            if key in seen_relationships or rev_key in seen_relationships:
                issues.append(f"Duplicate relationship: {rel.source} -> {rel.target}")
            seen_relationships.add(key)

        for rel in kg.relationships:
            source_exists = any(e.name == rel.source for e in kg.entities)
            target_exists = any(e.name == rel.target for e in kg.entities)
            if not source_exists:
                issues.append(f"Relationship source not in entities: {rel.source}")
            if not target_exists:
                issues.append(f"Relationship target not in entities: {rel.target}")

        if kg.metadata.quality_score == 0.0 and (kg.entity_count() > 0 or kg.keyword_count() > 0):
            issues.append("Quality score not computed")

        return issues

    def compute_quality_score(self, kg: KnowledgeGraph) -> float:
        score = 0.0
        if kg.entity_count() >= 5:
            score += 20
        elif kg.entity_count() >= 2:
            score += 10
        else:
            score += 5

        if kg.keyword_count() >= 10:
            score += 20
        elif kg.keyword_count() >= 5:
            score += 15
        else:
            score += 5

        if kg.relationship_count() >= 5:
            score += 15
        elif kg.relationship_count() >= 2:
            score += 10

        if len(kg.facts) >= 3:
            score += 10
        elif len(kg.facts) >= 1:
            score += 5

        if len(kg.timeline) >= 1:
            score += 5
        if len(kg.pain_points) >= 1:
            score += 5
        if len(kg.solutions) >= 1:
            score += 5
        if len(kg.quotes) >= 1:
            score += 5
        if len(kg.definitions) >= 2:
            score += 5
        if len(kg.semantic_clusters) >= 2:
            score += 5

        return min(100.0, score)

    def deduplicate(self, kg: KnowledgeGraph) -> KnowledgeGraph:
        seen_entities: set[str] = set()
        unique_entities = []
        for entity in kg.entities:
            if entity.name.lower() not in seen_entities:
                seen_entities.add(entity.name.lower())
                unique_entities.append(entity)
        kg.entities = unique_entities

        seen_keywords: set[str] = set()
        unique_keywords = []
        for kw in kg.keywords:
            if kw.keyword.lower() not in seen_keywords:
                seen_keywords.add(kw.keyword.lower())
                unique_keywords.append(kw)
        kg.keywords = unique_keywords

        return kg
