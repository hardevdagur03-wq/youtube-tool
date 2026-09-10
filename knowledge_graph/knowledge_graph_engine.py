"""Knowledge Graph Engine — orchestrates all extractors to build the knowledge graph.

Central orchestrator. No existing code is modified.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from knowledge_graph.knowledge_graph_models import (
    KnowledgeGraph,
    TopicInfo,
    GraphMetadata,
    Confidence,
    utc_now,
)
from knowledge_graph.entity_extractor import EntityExtractor
from knowledge_graph.keyword_extractor import KeywordExtractor
from knowledge_graph.fact_extractor import FactExtractor
from knowledge_graph.statistics_extractor import StatisticsExtractor
from knowledge_graph.timeline_builder import TimelineBuilder
from knowledge_graph.pain_point_detector import PainPointDetector
from knowledge_graph.solution_mapper import SolutionMapper
from knowledge_graph.quote_extractor import QuoteExtractor
from knowledge_graph.definition_extractor import DefinitionExtractor
from knowledge_graph.relationship_engine import RelationshipEngine
from knowledge_graph.semantic_cluster_engine import SemanticClusterEngine
from knowledge_graph.knowledge_graph_validator import KnowledgeGraphValidator

logger = logging.getLogger(__name__)


class KnowledgeGraphEngine:
    """Orchestrates all extractors to build a complete knowledge graph."""

    def __init__(self) -> None:
        self._entity_extractor = EntityExtractor()
        self._keyword_extractor = KeywordExtractor()
        self._fact_extractor = FactExtractor()
        self._statistics_extractor = StatisticsExtractor()
        self._timeline_builder = TimelineBuilder()
        self._pain_point_detector = PainPointDetector()
        self._solution_mapper = SolutionMapper()
        self._quote_extractor = QuoteExtractor()
        self._definition_extractor = DefinitionExtractor()
        self._relationship_engine = RelationshipEngine()
        self._cluster_engine = SemanticClusterEngine()
        self._validator = KnowledgeGraphValidator()

    def build(
        self,
        metadata: dict[str, Any] | None = None,
        transcript: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
        project_id: str = "",
        video_id: str = "",
    ) -> KnowledgeGraph:
        start = time.time()
        kg = KnowledgeGraph()

        try:
            kg.raw_analysis = analysis or {}
            used_artifacts = []
            if metadata:
                used_artifacts.append("metadata.json")
            if transcript:
                used_artifacts.append("transcript.json")
            if analysis:
                used_artifacts.append("analysis.json")

            # Build topic info from analysis
            if analysis and isinstance(analysis, dict):
                primary = analysis.get("primary_topic", "") or analysis.get("title", "")
                kg.topics = TopicInfo(
                    name=primary,
                    description=analysis.get("summary", {}).get("short", "") if isinstance(analysis.get("summary"), dict) else "",
                    confidence=Confidence.HIGH,
                    relevance_score=1.0,
                    subtopics=analysis.get("secondary_topics", []),
                )

                secondary = analysis.get("secondary_topics", [])
                if isinstance(secondary, list):
                    for st in secondary:
                        if isinstance(st, str):
                            kg.secondary_topics.append(TopicInfo(
                                name=st,
                                confidence=Confidence.MEDIUM,
                                relevance_score=0.5,
                            ))

            # Run all extractors
            kg.entities = self._entity_extractor.extract(analysis)
            kg.keywords = self._keyword_extractor.extract(analysis)
            kg.facts = self._fact_extractor.extract(transcript, analysis)
            kg.statistics = self._statistics_extractor.extract(transcript)
            kg.timeline = self._timeline_builder.build(transcript)
            kg.pain_points = self._pain_point_detector.detect(transcript, analysis)
            kg.solutions = self._solution_mapper.map(
                analysis,
                [p.problem for p in kg.pain_points],
            )
            kg.quotes = self._quote_extractor.extract(transcript)
            kg.definitions = self._definition_extractor.extract(transcript, analysis)

            # Build relationships
            kg.relationships = self._relationship_engine.build(kg.entities, analysis)

            # Build semantic clusters
            kg.semantic_clusters = self._cluster_engine.cluster(kg.entities, kg.keywords)

            # Deduplicate
            kg = self._validator.deduplicate(kg)

            # Quality
            quality = self._validator.compute_quality_score(kg)
            issues = self._validator.validate(kg)
            kg.warnings = [i for i in issues if "duplicate" in i.lower() or "score" in i.lower()]
            kg.errors = [i for i in issues if "too few" in i.lower()]

            # Metadata
            elapsed = (time.time() - start) * 1000
            kg.metadata = GraphMetadata(
                version="1.0",
                created_at=utc_now(),
                project_id=project_id,
                video_id=video_id,
                source_artifacts=used_artifacts,
                extraction_time_ms=round(elapsed, 1),
                total_entities=kg.entity_count(),
                total_relationships=kg.relationship_count(),
                total_facts=kg.fact_count(),
                quality_score=round(quality, 1),
            )

            logger.info(
                "Knowledge graph built: entities=%d, rels=%d, facts=%d, keywords=%d, quality=%.1f, time=%.0fms",
                kg.entity_count(), kg.relationship_count(), kg.fact_count(),
                kg.keyword_count(), quality, elapsed,
            )

        except Exception as exc:
            logger.error("Knowledge graph build failed: %s", exc)
            kg.errors.append(f"Build failed: {exc}")

        return kg
