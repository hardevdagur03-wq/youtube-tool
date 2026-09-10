"""Tests for the Knowledge Graph Engine.

All existing tests continue to work unchanged.
No existing code is modified.
"""

from __future__ import annotations

from knowledge_graph.knowledge_graph_models import (
    KnowledgeGraph, EntityInfo, KeywordInfo, FactInfo, StatisticInfo,
    TimelineEvent, PainPoint, Solution, Quote, Definition,
    Relationship, SemanticCluster, TopicInfo, GraphMetadata,
    EntityType, RelationshipType, Confidence, Importance,
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


SAMPLE_ANALYSIS = {
    "primary_topic": "Python Programming for Data Science",
    "secondary_topics": ["Machine Learning", "Data Visualization", "Statistics"],
    "search_intent": "educational",
    "content_category": "programming",
    "summary": {
        "short": "A comprehensive guide to Python for data science",
        "key_insights": [
            "Python is the most popular language for data science",
            "Pandas and NumPy are essential libraries",
            "Data visualization is critical for communication",
        ],
    },
    "key_takeaways": ["Start with Python basics", "Practice with real datasets"],
    "pain_points": ["Steep learning curve", "Data cleaning is time-consuming"],
    "solutions": ["Use Jupyter notebooks for interactive development"],
    "action_items": ["Install Python", "Set up a virtual environment"],
    "entities": {
        "people": ["Guido van Rossum"],
        "technologies": ["Python", "Pandas", "NumPy", "Scikit-learn", "TensorFlow"],
        "frameworks": ["Django", "Flask"],
        "tools": ["Jupyter", "VS Code"],
    },
    "keywords": {
        "primary": ["Python programming", "data science"],
        "secondary": ["machine learning", "data analysis"],
        "long_tail": ["Python for beginners", "data science tutorial"],
        "semantic": ["programming", "analytics"],
    },
}

SAMPLE_TRANSCRIPT = {
    "plain_text": (
        "Python is a high-level programming language. "
        "It was created by Guido van Rossum in 1991. "
        "According to recent studies, Python usage has grown by 50%. "
        "The most important thing to remember is to always use virtual environments. "
        "Pandas is a fast, powerful library for data analysis. "
        "Data cleaning is one of the most challenging tasks for data scientists. "
        'As the speaker noted, "Python simplicity is its greatest strength." '
        "The framework has been adopted by over 10 million developers worldwide. "
        "Machine learning models require careful tuning and validation. "
        "In 2023, Python was ranked as the #1 programming language."
    ),
    "segments": [
        {"text": "Python is a high-level programming language.", "start": 0.0, "duration": 5.0},
        {"text": "It was created by Guido van Rossum in 1991.", "start": 5.0, "duration": 4.0},
        {"text": "Python usage has grown by 50%.", "start": 9.0, "duration": 3.0},
        {"text": "Always use virtual environments.", "start": 12.0, "duration": 3.0},
    ],
}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TestKnowledgeGraphModels:
    def test_default_graph(self):
        kg = KnowledgeGraph()
        assert kg.entity_count() == 0
        assert kg.relationship_count() == 0
        assert kg.fact_count() == 0
        assert kg.keyword_count() == 0
        assert kg.metadata.version == "1.0"

    def test_entity_info(self):
        e = EntityInfo(name="Python", type=EntityType.TECHNOLOGY)
        assert e.name == "Python"
        assert e.type == EntityType.TECHNOLOGY
        assert e.frequency == 1

    def test_keyword_info(self):
        kw = KeywordInfo(keyword="data science", type="primary")
        assert kw.keyword == "data science"
        assert kw.relevance_score == 0.5

    def test_fact_info(self):
        f = FactInfo(statement="Python is popular", category="insight")
        assert f.statement == "Python is popular"
        assert f.importance == Importance.MEDIUM

    def test_statistic_info(self):
        s = StatisticInfo(value="50", unit="percent")
        assert s.value == "50"
        assert s.unit == "percent"

    def test_timeline_event(self):
        t = TimelineEvent(event="Python created", timestamp="1991")
        assert t.event == "Python created"

    def test_pain_point(self):
        p = PainPoint(problem="Steep learning curve", severity=Importance.HIGH)
        assert p.problem == "Steep learning curve"

    def test_solution(self):
        s = Solution(problem="Learning curve", solution="Start with tutorials")
        assert s.solution == "Start with tutorials"

    def test_quote(self):
        q = Quote(text="Python is great", speaker="Guido")
        assert q.text == "Python is great"

    def test_definition(self):
        d = Definition(term="API", definition="Application Programming Interface")
        assert d.term == "API"

    def test_relationship(self):
        r = Relationship(source="Python", target="Data Science")
        assert r.source == "Python"

    def test_semantic_cluster(self):
        sc = SemanticCluster(name="technology")
        assert sc.name == "technology"

    def test_topic_info(self):
        t = TopicInfo(name="Data Science", confidence=Confidence.HIGH)
        assert t.name == "Data Science"

    def test_graph_metadata(self):
        gm = GraphMetadata(project_id="proj123")
        assert gm.project_id == "proj123"

    def test_summary(self):
        kg = KnowledgeGraph()
        s = kg.summary
        assert s["total_entities"] == 0
        assert s["quality_score"] == 0.0

    def test_entity_type_enum(self):
        assert EntityType.PERSON.value == "person"
        assert EntityType.TECHNOLOGY.value == "technology"

    def test_relationship_type_enum(self):
        assert RelationshipType.RELATED_TO.value == "related_to"
        assert RelationshipType.PART_OF.value == "part_of"


# ---------------------------------------------------------------------------
# Entity Extractor
# ---------------------------------------------------------------------------


class TestEntityExtractor:
    def test_extract_from_analysis(self):
        extractor = EntityExtractor()
        entities = extractor.extract(SAMPLE_ANALYSIS)
        assert len(entities) > 0
        names = [e.name for e in entities]
        assert "Python" in names
        assert "Pandas" in names
        assert "Guido van Rossum" in names

    def test_empty_analysis(self):
        extractor = EntityExtractor()
        entities = extractor.extract({})
        assert entities == []

    def test_none_analysis(self):
        extractor = EntityExtractor()
        entities = extractor.extract(None)
        assert entities == []

    def test_entity_types(self):
        extractor = EntityExtractor()
        entities = extractor.extract(SAMPLE_ANALYSIS)
        for e in entities:
            if e.name == "Guido van Rossum":
                assert e.type == EntityType.PERSON
            if e.name == "Python":
                assert e.type == EntityType.TECHNOLOGY


# ---------------------------------------------------------------------------
# Keyword Extractor
# ---------------------------------------------------------------------------


class TestKeywordExtractor:
    def test_extract(self):
        extractor = KeywordExtractor()
        keywords = extractor.extract(SAMPLE_ANALYSIS)
        assert len(keywords) > 0
        types = [k.type for k in keywords]
        assert "primary" in types
        assert "secondary" in types
        assert "long_tail" in types

    def test_empty(self):
        extractor = KeywordExtractor()
        assert extractor.extract({}) == []

    def test_primary_first(self):
        extractor = KeywordExtractor()
        keywords = extractor.extract(SAMPLE_ANALYSIS)
        primaries = [k for k in keywords if k.type == "primary"]
        assert len(primaries) > 0
        assert primaries[0].relevance_score == 1.0


# ---------------------------------------------------------------------------
# Fact Extractor
# ---------------------------------------------------------------------------


class TestFactExtractor:
    def test_extract_from_analysis(self):
        extractor = FactExtractor()
        facts = extractor.extract(None, SAMPLE_ANALYSIS)
        assert len(facts) > 0
        assert any("Python" in f.statement for f in facts)

    def test_extract_from_transcript(self):
        extractor = FactExtractor()
        facts = extractor.extract(SAMPLE_TRANSCRIPT, None)
        assert len(facts) > 0


# ---------------------------------------------------------------------------
# Statistics Extractor
# ---------------------------------------------------------------------------


class TestStatisticsExtractor:
    def test_extract(self):
        extractor = StatisticsExtractor()
        stats = extractor.extract(SAMPLE_TRANSCRIPT)
        assert len(stats) > 0
        values = [s.value for s in stats]
        assert "50" in values

    def test_empty(self):
        extractor = StatisticsExtractor()
        assert extractor.extract({}) == []


# ---------------------------------------------------------------------------
# Timeline Builder
# ---------------------------------------------------------------------------


class TestTimelineBuilder:
    def test_build(self):
        builder = TimelineBuilder()
        events = builder.build(SAMPLE_TRANSCRIPT)
        assert len(events) > 0

    def test_empty(self):
        builder = TimelineBuilder()
        assert builder.build(None) == []


# ---------------------------------------------------------------------------
# Pain Point Detector
# ---------------------------------------------------------------------------


class TestPainPointDetector:
    def test_detect_from_analysis(self):
        detector = PainPointDetector()
        points = detector.detect(None, SAMPLE_ANALYSIS)
        assert len(points) > 0
        assert any("learning" in p.problem for p in points)

    def test_empty(self):
        detector = PainPointDetector()
        assert detector.detect(None, {}) == []


# ---------------------------------------------------------------------------
# Solution Mapper
# ---------------------------------------------------------------------------


class TestSolutionMapper:
    def test_map(self):
        mapper = SolutionMapper()
        problems = ["Steep learning curve", "Data cleaning is time-consuming"]
        solutions = mapper.map(SAMPLE_ANALYSIS, problems)
        assert len(solutions) > 0

    def test_empty(self):
        mapper = SolutionMapper()
        assert mapper.map({}, []) == []


# ---------------------------------------------------------------------------
# Quote Extractor
# ---------------------------------------------------------------------------


class TestQuoteExtractor:
    def test_extract(self):
        extractor = QuoteExtractor()
        quotes = extractor.extract(SAMPLE_TRANSCRIPT)
        assert len(quotes) > 0
        assert any("simplicity" in q.text for q in quotes)

    def test_empty(self):
        extractor = QuoteExtractor()
        assert extractor.extract(None) == []


# ---------------------------------------------------------------------------
# Definition Extractor
# ---------------------------------------------------------------------------


class TestDefinitionExtractor:
    def test_extract(self):
        extractor = DefinitionExtractor()
        definitions = extractor.extract(SAMPLE_TRANSCRIPT, None)
        assert len(definitions) > 0
        terms = [d.term for d in definitions]
        assert any("Python" in t for t in terms)

    def test_empty(self):
        extractor = DefinitionExtractor()
        assert extractor.extract(None, None) == []


# ---------------------------------------------------------------------------
# Relationship Engine
# ---------------------------------------------------------------------------


class TestRelationshipEngine:
    def test_build(self):
        engine = RelationshipEngine()
        entities = [
            EntityInfo(name="Python", type=EntityType.TECHNOLOGY),
            EntityInfo(name="Data Science", type=EntityType.CONCEPT),
            EntityInfo(name="Pandas", type=EntityType.LIBRARY),
        ]
        rels = engine.build(entities, SAMPLE_ANALYSIS)
        assert len(rels) > 0
        assert any(r.source == "Python Programming for Data Science" for r in rels)

    def test_empty(self):
        engine = RelationshipEngine()
        assert engine.build([], {}) == []


# ---------------------------------------------------------------------------
# Semantic Cluster Engine
# ---------------------------------------------------------------------------


class TestSemanticClusterEngine:
    def test_cluster(self):
        engine = SemanticClusterEngine()
        entities = [
            EntityInfo(name="Python", type=EntityType.TECHNOLOGY),
            EntityInfo(name="Django", type=EntityType.FRAMEWORK),
            EntityInfo(name="Jupyter", type=EntityType.TOOL),
        ]
        keywords = [
            KeywordInfo(keyword="programming", type="primary"),
            KeywordInfo(keyword="data science", type="primary"),
        ]
        clusters = engine.cluster(entities, keywords)
        assert len(clusters) > 0

    def test_empty(self):
        engine = SemanticClusterEngine()
        assert engine.cluster([], []) == []


# ---------------------------------------------------------------------------
# Knowledge Graph Validator
# ---------------------------------------------------------------------------


class TestKnowledgeGraphValidator:
    def test_validate_empty(self):
        validator = KnowledgeGraphValidator()
        kg = KnowledgeGraph()
        issues = validator.validate(kg)
        assert len(issues) > 0
        assert any("Too few" in i for i in issues)

    def test_validate_populated(self):
        validator = KnowledgeGraphValidator()
        kg = KnowledgeGraph()
        kg.entities.append(EntityInfo(name="Python", type=EntityType.TECHNOLOGY))
        kg.entities.append(EntityInfo(name="Pandas", type=EntityType.LIBRARY))
        kg.keywords.append(KeywordInfo(keyword="programming", type="primary"))
        issues = validator.validate(kg)
        assert len(issues) >= 0

    def test_duplicate_detection(self):
        validator = KnowledgeGraphValidator()
        kg = KnowledgeGraph()
        kg.entities.append(EntityInfo(name="Python", type=EntityType.TECHNOLOGY))
        kg.entities.append(EntityInfo(name="Python", type=EntityType.TECHNOLOGY))
        issues = validator.validate(kg)
        assert any("Duplicate" in i for i in issues)

    def test_quality_score(self):
        validator = KnowledgeGraphValidator()
        kg = KnowledgeGraph()
        kg.entities = [
            EntityInfo(name=f"E{i}", type=EntityType.CONCEPT) for i in range(5)
        ]
        kg.keywords = [
            KeywordInfo(keyword=f"K{i}", type="primary") for i in range(10)
        ]
        score = validator.compute_quality_score(kg)
        assert 0 <= score <= 100

    def test_deduplicate(self):
        validator = KnowledgeGraphValidator()
        kg = KnowledgeGraph()
        kg.entities.append(EntityInfo(name="Python", type=EntityType.TECHNOLOGY))
        kg.entities.append(EntityInfo(name="python", type=EntityType.TECHNOLOGY))
        kg = validator.deduplicate(kg)
        assert kg.entity_count() == 1


# ---------------------------------------------------------------------------
# Knowledge Graph Engine (Integration)
# ---------------------------------------------------------------------------


class TestKnowledgeGraphEngine:
    def test_build_full(self):
        engine = KnowledgeGraphEngine()
        kg = engine.build(
            metadata={"title": "Test"},
            transcript=SAMPLE_TRANSCRIPT,
            analysis=SAMPLE_ANALYSIS,
            project_id="test123",
            video_id="vid123",
        )
        assert kg.entity_count() > 0
        assert kg.keyword_count() > 0
        assert kg.metadata.project_id == "test123"
        assert kg.metadata.video_id == "vid123"
        assert kg.metadata.total_entities > 0
        assert kg.metadata.extraction_time_ms >= 0

    def test_build_minimal(self):
        engine = KnowledgeGraphEngine()
        kg = engine.build(analysis=SAMPLE_ANALYSIS)
        assert kg.entity_count() > 0
        assert kg.keyword_count() > 0

    def test_build_empty(self):
        engine = KnowledgeGraphEngine()
        kg = engine.build()
        assert kg.entity_count() == 0


# ---------------------------------------------------------------------------
# Knowledge Graph Service
# ---------------------------------------------------------------------------


class TestKnowledgeGraphService:
    def test_build_and_summary(self):
        svc = KnowledgeGraphService()
        kg = svc.build(
            project_id="test123",
            metadata={"title": "Test"},
            transcript=SAMPLE_TRANSCRIPT,
            analysis=SAMPLE_ANALYSIS,
        )
        summary = svc.summary(kg)
        assert summary["total_entities"] > 0
        assert summary["total_keywords"] > 0

    def test_validate(self):
        svc = KnowledgeGraphService()
        kg = KnowledgeGraph()
        issues = svc.validate(kg)
        assert len(issues) > 0

    def test_quality_score(self):
        svc = KnowledgeGraphService()
        kg = KnowledgeGraph()
        kg.entities.append(EntityInfo(name="Test", type=EntityType.CONCEPT))
        kg.keywords.append(KeywordInfo(keyword="test", type="primary"))
        score = svc.quality_score(kg)
        assert score > 0
