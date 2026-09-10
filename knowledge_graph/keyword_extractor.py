"""Keyword Extractor — extracts and clusters keywords from existing analysis output.

Consumes analysis.json. No external API calls.
No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from knowledge_graph.knowledge_graph_models import KeywordInfo, Confidence

logger = logging.getLogger(__name__)


class KeywordExtractor:
    """Extracts and clusters keywords from existing analysis."""

    def extract(self, analysis: dict[str, Any]) -> list[KeywordInfo]:
        keywords: list[KeywordInfo] = []
        seen: set[str] = set()
        kw_data = analysis.get("keywords", {}) if analysis else {}

        if not isinstance(kw_data, dict):
            return keywords

        type_mapping = {
            "primary": ("primary", 1.0),
            "secondary": ("secondary", 0.7),
            "long_tail": ("long_tail", 0.5),
            "semantic": ("semantic", 0.4),
            "lsi": ("lsi", 0.3),
            "related_topics": ("related", 0.3),
        }

        for field, (kw_type, base_relevance) in type_mapping.items():
            items = kw_data.get(field, [])
            if isinstance(items, list):
                for i, kw in enumerate(items):
                    if isinstance(kw, str) and kw.lower() not in seen:
                        seen.add(kw.lower())
                        keywords.append(KeywordInfo(
                            keyword=kw,
                            type=kw_type,
                            cluster=kw_type,
                            relevance_score=max(0.1, base_relevance - (i * 0.05)),
                            frequency=1,
                            confidence=Confidence.HIGH,
                        ))

        if analysis:
            intent = ""
            category = ""
            if isinstance(analysis, dict):
                intent = analysis.get("search_intent", "")
                category = analysis.get("content_category", "")
            for kw in keywords:
                if intent:
                    kw.intent = intent
                if category:
                    kw.cluster = category

        return keywords
