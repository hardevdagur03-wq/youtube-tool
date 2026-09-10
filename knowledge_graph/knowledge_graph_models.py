"""Pydantic models for the Knowledge Graph.

Single source of truth for all extracted semantic information.
No existing code is modified.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    PERSON = "person"
    COMPANY = "company"
    PRODUCT = "product"
    TECHNOLOGY = "technology"
    FRAMEWORK = "framework"
    LIBRARY = "library"
    TOOL = "tool"
    ORGANIZATION = "organization"
    LOCATION = "location"
    STANDARD = "standard"
    LANGUAGE = "language"
    API = "api"
    PLATFORM = "platform"
    RESEARCH_PAPER = "research_paper"
    BOOK = "book"
    EVENT = "event"
    CONCEPT = "concept"
    OTHER = "other"


class RelationshipType(str, Enum):
    RELATED_TO = "related_to"
    PART_OF = "part_of"
    DEPENDS_ON = "depends_on"
    USES = "uses"
    PRODUCES = "produces"
    PREREQUISITE = "prerequisite"
    ALTERNATIVE = "alternative"
    COMPARED_TO = "compared_to"
    SOLVES = "solves"
    CAUSES = "causes"
    EXAMPLE_OF = "example_of"
    TYPE_OF = "type_of"
    BELONGS_TO = "belongs_to"
    RECOMMENDS = "recommends"
    CONTRADICTS = "contradicts"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Importance(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TRIVIAL = "trivial"


# ---------------------------------------------------------------------------
# Core Models
# ---------------------------------------------------------------------------


class TopicInfo(BaseModel):
    name: str = ""
    description: str = ""
    confidence: Confidence = Confidence.MEDIUM
    relevance_score: float = 0.5
    subtopics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class EntityInfo(BaseModel):
    name: str
    type: EntityType = EntityType.OTHER
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    frequency: int = 1
    importance_score: float = 0.5
    confidence: Confidence = Confidence.MEDIUM
    mentions: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    source_segments: list[int] = Field(default_factory=list)


class KeywordInfo(BaseModel):
    keyword: str
    type: str = "primary"
    cluster: str = ""
    relevance_score: float = 0.5
    frequency: int = 1
    search_volume: str = ""
    intent: str = ""
    confidence: Confidence = Confidence.MEDIUM


class FactInfo(BaseModel):
    statement: str
    source_timestamp: float = 0.0
    confidence: Confidence = Confidence.MEDIUM
    category: str = ""
    importance: Importance = Importance.MEDIUM
    context: str = ""
    evidence: str = ""
    related_entities: list[str] = Field(default_factory=list)
    source_segment_index: int = -1


class StatisticInfo(BaseModel):
    value: str
    unit: str = ""
    meaning: str = ""
    context: str = ""
    category: str = ""
    source_timestamp: float = 0.0
    confidence: Confidence = Confidence.MEDIUM
    importance: Importance = Importance.MEDIUM
    source_segment_index: int = -1


class TimelineEvent(BaseModel):
    timestamp: str = ""
    event: str
    description: str = ""
    importance: Importance = Importance.MEDIUM
    referenced_entities: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    source_segment_index: int = -1


class PainPoint(BaseModel):
    problem: str
    severity: Importance = Importance.MEDIUM
    category: str = ""
    context: str = ""
    evidence: str = ""
    related_solutions: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM


class Solution(BaseModel):
    problem: str
    solution: str
    steps: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    dependencies: list[str] = Field(default_factory=list)


class Quote(BaseModel):
    text: str
    speaker: str = ""
    source_timestamp: float = 0.0
    context: str = ""
    importance: Importance = Importance.MEDIUM
    confidence: Confidence = Confidence.MEDIUM
    source_segment_index: int = -1


class Definition(BaseModel):
    term: str
    definition: str
    category: str = ""
    difficulty: str = "intermediate"
    confidence: Confidence = Confidence.MEDIUM
    source_segment_index: int = -1


class Relationship(BaseModel):
    source: str
    target: str
    type: RelationshipType = RelationshipType.RELATED_TO
    weight: float = 1.0
    context: str = ""
    confidence: Confidence = Confidence.MEDIUM


class SemanticCluster(BaseModel):
    name: str
    description: str = ""
    entities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    importance_score: float = 0.5


class GraphMetadata(BaseModel):
    version: str = "1.0"
    created_at: str = ""
    project_id: str = ""
    video_id: str = ""
    source_artifacts: list[str] = Field(default_factory=list)
    extraction_time_ms: float = 0.0
    total_entities: int = 0
    total_relationships: int = 0
    total_facts: int = 0
    quality_score: float = 0.0


class KnowledgeGraph(BaseModel):
    """Complete knowledge graph — single source of semantic truth."""

    metadata: GraphMetadata = Field(default_factory=GraphMetadata)

    topics: TopicInfo = Field(default_factory=TopicInfo)
    secondary_topics: list[TopicInfo] = Field(default_factory=list)

    entities: list[EntityInfo] = Field(default_factory=list)
    keywords: list[KeywordInfo] = Field(default_factory=list)
    facts: list[FactInfo] = Field(default_factory=list)
    statistics: list[StatisticInfo] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    pain_points: list[PainPoint] = Field(default_factory=list)
    solutions: list[Solution] = Field(default_factory=list)
    quotes: list[Quote] = Field(default_factory=list)
    definitions: list[Definition] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    semantic_clusters: list[SemanticCluster] = Field(default_factory=list)

    raw_analysis: dict[str, Any] = Field(default_factory=dict)

    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def entity_count(self) -> int:
        return len(self.entities)

    def relationship_count(self) -> int:
        return len(self.relationships)

    def fact_count(self) -> int:
        return len(self.facts)

    def keyword_count(self) -> int:
        return len(self.keywords)

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "total_entities": self.entity_count(),
            "total_relationships": self.relationship_count(),
            "total_facts": self.fact_count(),
            "total_keywords": self.keyword_count(),
            "total_statistics": len(self.statistics),
            "total_timeline_events": len(self.timeline),
            "total_pain_points": len(self.pain_points),
            "total_solutions": len(self.solutions),
            "total_quotes": len(self.quotes),
            "total_definitions": len(self.definitions),
            "total_semantic_clusters": len(self.semantic_clusters),
            "quality_score": self.metadata.quality_score,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
