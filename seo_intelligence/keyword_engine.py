"""Keyword Engine — primary, secondary, LSI, and long-tail keyword strategy.

Consumes knowledge_graph.json and analysis.json. No external API calls.
No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from seo_intelligence.seo_models import (
    KeywordStrategy, KeywordInfo, KeywordType, CompetitionLevel,
)

logger = logging.getLogger(__name__)


class KeywordEngine:
    """Generates complete keyword strategy from knowledge graph and analysis."""

    def generate(
        self,
        knowledge_graph: dict[str, Any] | None,
        analysis: dict[str, Any] | None,
    ) -> KeywordStrategy:
        strategy = KeywordStrategy()
        seen_keywords: set[str] = set()

        kg = knowledge_graph or {}
        analysis_data = analysis or {}

        # Primary keyword from analysis or KG
        primary = ""
        if isinstance(analysis_data, dict):
            primary = analysis_data.get("primary_topic", "") or analysis_data.get("title", "")
        if not primary and isinstance(kg, dict):
            topics = kg.get("topics", {})
            if isinstance(topics, dict):
                primary = topics.get("name", "")
        if not primary:
            kw_data = analysis_data.get("keywords", {}) if isinstance(analysis_data, dict) else {}
            if isinstance(kw_data, dict):
                primaries = kw_data.get("primary", [])
                if primaries and isinstance(primaries, list):
                    primary = str(primaries[0]) if primaries else ""

        if primary:
            strategy.primary_keyword = primary
            seen_keywords.add(primary.lower())
            intent = ""
            if isinstance(analysis_data, dict):
                intent = analysis_data.get("search_intent", "")
            strategy.primary_intent = intent or "informational"
            strategy.primary_difficulty = 0.5

        # Secondary keywords from analysis
        if isinstance(analysis_data, dict):
            kw_data = analysis_data.get("keywords", {})
            if isinstance(kw_data, dict):
                for field, kw_type, priority_base in [
                    ("secondary", KeywordType.SECONDARY, 8),
                    ("semantic", KeywordType.SEMANTIC, 6),
                    ("lsi", KeywordType.LSI, 5),
                    ("long_tail", KeywordType.LONG_TAIL, 4),
                ]:
                    items = kw_data.get(field, [])
                    if isinstance(items, list):
                        for i, kw in enumerate(items):
                            kw_str = str(kw) if not isinstance(kw, str) else kw
                            if kw_str.lower() not in seen_keywords:
                                seen_keywords.add(kw_str.lower())
                                strategy.secondary_keywords.append(KeywordInfo(
                                    keyword=kw_str,
                                    type=kw_type,
                                    priority=max(1, priority_base - i),
                                    relevance=max(0.3, 1.0 - (i * 0.08)),
                                ))

        # Entity keywords from KG
        if isinstance(kg, dict):
            entities = kg.get("entities", [])
            if isinstance(entities, list):
                for entity in entities:
                    if isinstance(entity, dict):
                        name = entity.get("name", "")
                        if name and name.lower() not in seen_keywords:
                            seen_keywords.add(name.lower())
                            importance = entity.get("importance_score", 0.5)
                            strategy.entity_keywords.append(name)
                            if importance > 0.6:
                                strategy.secondary_keywords.append(KeywordInfo(
                                    keyword=name,
                                    type=KeywordType.SEMANTIC,
                                    relevance=importance,
                                    priority=int(importance * 8),
                                ))

            # Question keywords from KG facts
            facts = kg.get("facts", [])
            if isinstance(facts, list):
                for fact in facts:
                    if isinstance(fact, dict):
                        statement = fact.get("statement", "")
                        if statement and len(statement) > 20 and "?" in statement:
                            q = statement.split("?")[0] + "?"
                            if q.lower() not in seen_keywords and len(q) < 100:
                                seen_keywords.add(q.lower())
                                strategy.question_keywords.append(q)

            # LSI from semantic clusters
            clusters = kg.get("semantic_clusters", [])
            if isinstance(clusters, list):
                for cluster in clusters:
                    if isinstance(cluster, dict):
                        for kw in cluster.get("keywords", []):
                            if isinstance(kw, str) and kw.lower() not in seen_keywords:
                                seen_keywords.add(kw.lower())
                                strategy.lsi_keywords.append(kw)

        # Populate lists from secondary keywords
        for sk in strategy.secondary_keywords:
            if sk.type == KeywordType.LSI:
                strategy.lsi_keywords.append(sk.keyword)
            elif sk.type == KeywordType.LONG_TAIL:
                strategy.long_tail_keywords.append(sk.keyword)
            elif sk.type == KeywordType.SEMANTIC:
                strategy.semantic_keywords.append(sk.keyword)

        strategy.total_keyword_count = len(seen_keywords)

        logger.info(
            "Keyword strategy generated: primary='%s', total=%d, lsi=%d, long_tail=%d",
            strategy.primary_keyword, strategy.total_keyword_count,
            len(strategy.lsi_keywords), len(strategy.long_tail_keywords),
        )

        return strategy
