"""Semantic Cluster Engine — groups information into semantic clusters.

Clusters entities, keywords, and topics by semantic similarity.
No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from knowledge_graph.knowledge_graph_models import (
    EntityInfo,
    KeywordInfo,
    SemanticCluster,
)

logger = logging.getLogger(__name__)

DEFAULT_CLUSTERS = {
    "technology": {"technology", "api", "platform", "tool", "framework", "library", "language", "standard"},
    "ai_ml": {"ai", "ml", "machine learning", "deep learning", "neural", "llm", "gpt", "transformer", "model"},
    "data": {"data", "database", "analytics", "statistics", "metric", "kpi", "dashboard", "report"},
    "development": {"code", "programming", "software", "development", "engineering", "deploy", "devops", "ci/cd"},
    "business": {"business", "startup", "company", "enterprise", "revenue", "growth", "market", "strategy"},
    "design": {"design", "ux", "ui", "interface", "user experience", "accessibility", "responsive"},
    "security": {"security", "privacy", "auth", "encryption", "compliance", "gdpr", "vulnerability"},
    "cloud": {"cloud", "aws", "azure", "gcp", "serverless", "kubernetes", "docker", "container"},
    "content": {"content", "blog", "seo", "writing", "marketing", "social", "video", "transcript"},
}


class SemanticClusterEngine:
    """Groups entities and keywords into semantic clusters."""

    def cluster(
        self,
        entities: list[EntityInfo],
        keywords: list[KeywordInfo],
    ) -> list[SemanticCluster]:
        clusters: dict[str, SemanticCluster] = {}
        for name, topics in DEFAULT_CLUSTERS.items():
            clusters[name] = SemanticCluster(name=name, description=f"Cluster for {name}")

        for entity in entities:
            for cluster_name, topics in DEFAULT_CLUSTERS.items():
                if any(t in entity.name.lower() for t in topics):
                    if entity.name not in clusters[cluster_name].entities:
                        clusters[cluster_name].entities.append(entity.name)
                    if entity.type.value not in clusters[cluster_name].topics:
                        clusters[cluster_name].topics.append(entity.type.value)

        for kw in keywords:
            for cluster_name, topics in DEFAULT_CLUSTERS.items():
                if any(t in kw.keyword.lower() for t in topics):
                    if kw.keyword not in clusters[cluster_name].keywords:
                        clusters[cluster_name].keywords.append(kw.keyword)

        for cluster in clusters.values():
            score = (len(cluster.entities) * 0.3 + len(cluster.keywords) * 0.2 +
                     len(cluster.topics) * 0.5)
            cluster.importance_score = min(1.0, score / 10.0)

        return [c for c in clusters.values() if c.entities or c.keywords]
