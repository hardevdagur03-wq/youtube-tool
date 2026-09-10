"""Knowledge Graph Engine — semantic intelligence layer for the platform.

Consumes existing metadata.json, transcript.json, and analysis.json.
Generates a reusable knowledge_graph.json for all downstream stages.
No external API calls. No modifications to existing modules.
"""

from knowledge_graph.knowledge_graph_models import (
    KnowledgeGraph,
    TopicInfo,
    EntityInfo,
    KeywordInfo,
    FactInfo,
    StatisticInfo,
    TimelineEvent,
    PainPoint,
    Solution,
    Quote,
    Definition,
    Relationship,
    SemanticCluster,
    GraphMetadata,
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
from knowledge_graph.knowledge_graph_engine import KnowledgeGraphEngine
from knowledge_graph.knowledge_graph_service import KnowledgeGraphService

__all__ = [
    "KnowledgeGraph", "TopicInfo", "EntityInfo", "KeywordInfo",
    "FactInfo", "StatisticInfo", "TimelineEvent", "PainPoint",
    "Solution", "Quote", "Definition", "Relationship", "SemanticCluster",
    "GraphMetadata",
    "EntityExtractor", "KeywordExtractor", "FactExtractor",
    "StatisticsExtractor", "TimelineBuilder", "PainPointDetector",
    "SolutionMapper", "QuoteExtractor", "DefinitionExtractor",
    "RelationshipEngine", "SemanticClusterEngine",
    "KnowledgeGraphValidator", "KnowledgeGraphEngine",
    "KnowledgeGraphService",
]
