from __future__ import annotations

import pytest

SAMPLE_ANALYSIS = {
    "primary_topic": "Python Programming for Data Science",
    "secondary_topics": ["Machine Learning", "Data Visualization", "Statistics"],
    "search_intent": "educational",
    "content_category": "programming",
    "summary": {"short": "A comprehensive guide", "key_insights": ["Python is popular"]},
    "key_takeaways": ["Start with Python basics"],
    "pain_points": ["Steep learning curve", "Data cleaning is time-consuming"],
    "solutions": ["Use Jupyter notebooks"],
    "entities": {
        "people": ["Guido van Rossum"],
        "technologies": ["Python", "Pandas", "NumPy"],
        "frameworks": ["Django"],
        "tools": ["Jupyter"],
    },
    "keywords": {
        "primary": ["Python programming", "data science"],
        "secondary": ["machine learning", "data analysis"],
        "long_tail": ["Python for beginners"],
        "semantic": ["programming", "analytics"],
    },
}

SAMPLE_TRANSCRIPT = {
    "plain_text": (
        "Python is a high-level programming language. "
        "It was created by Guido van Rossum in 1991. "
        "Python usage has grown by 50%. "
        "Pandas is a fast, powerful library for data analysis. "
        "Data cleaning is one of the most challenging tasks. "
        'As the speaker noted, "Python simplicity is its greatest strength." '
        "The framework has been adopted by over 10 million developers worldwide."
    ),
    "segments": [
        {"text": "Python is a high-level programming language.", "start": 0.0, "duration": 5.0},
        {"text": "It was created by Guido van Rossum in 1991.", "start": 5.0, "duration": 4.0},
    ],
}


class TestKnowledgeGraphModels:
    def test_default_graph(self):
        from knowledge_graph.knowledge_graph_models import KnowledgeGraph
        kg = KnowledgeGraph()
        assert kg.entity_count() == 0
        assert kg.relationship_count() == 0
        assert kg.metadata.version == "1.0"

    def test_entity_info(self):
        from knowledge_graph.knowledge_graph_models import EntityInfo, EntityType
        e = EntityInfo(name="Python", type=EntityType.TECHNOLOGY)
        assert e.name == "Python"
        assert e.frequency == 1

    def test_keyword_info(self):
        from knowledge_graph.knowledge_graph_models import KeywordInfo
        kw = KeywordInfo(keyword="data science", type="primary")
        assert kw.keyword == "data science"
        assert kw.relevance_score == 0.5

    def test_fact_info(self):
        from knowledge_graph.knowledge_graph_models import FactInfo, Importance
        f = FactInfo(statement="Python is popular", category="insight")
        assert f.importance == Importance.MEDIUM

    def test_enums(self):
        from knowledge_graph.knowledge_graph_models import EntityType, RelationshipType, Confidence
        assert EntityType.PERSON.value == "person"
        assert RelationshipType.RELATED_TO.value == "related_to"
        assert Confidence.HIGH.value == "high"


class TestEntityExtractor:
    def test_extract(self):
        from knowledge_graph.entity_extractor import EntityExtractor
        extractor = EntityExtractor()
        entities = extractor.extract(SAMPLE_ANALYSIS)
        assert len(entities) > 0
        names = [e.name for e in entities]
        assert "Python" in names

    def test_extract_empty(self):
        from knowledge_graph.entity_extractor import EntityExtractor
        extractor = EntityExtractor()
        entities = extractor.extract({})
        assert entities == []

    def test_extract_none(self):
        from knowledge_graph.entity_extractor import EntityExtractor
        extractor = EntityExtractor()
        entities = extractor.extract(None)
        assert entities == []


class TestKeywordExtractor:
    def test_extract(self):
        from knowledge_graph.keyword_extractor import KeywordExtractor
        extractor = KeywordExtractor()
        keywords = extractor.extract(SAMPLE_ANALYSIS)
        assert len(keywords) > 0
        types = [k.type for k in keywords]
        assert "primary" in types

    def test_extract_empty(self):
        from knowledge_graph.keyword_extractor import KeywordExtractor
        extractor = KeywordExtractor()
        assert extractor.extract({}) == []

    def test_primary_first(self):
        from knowledge_graph.keyword_extractor import KeywordExtractor
        extractor = KeywordExtractor()
        keywords = extractor.extract(SAMPLE_ANALYSIS)
        primaries = [k for k in keywords if k.type == "primary"]
        assert len(primaries) > 0
        assert primaries[0].relevance_score == 1.0


class TestFactExtractor:
    def test_extract_from_analysis(self):
        from knowledge_graph.fact_extractor import FactExtractor
        extractor = FactExtractor()
        facts = extractor.extract(None, SAMPLE_ANALYSIS)
        assert len(facts) > 0
        assert any("Python" in f.statement for f in facts)

    def test_extract_from_transcript(self):
        from knowledge_graph.fact_extractor import FactExtractor
        extractor = FactExtractor()
        facts = extractor.extract(SAMPLE_TRANSCRIPT, None)
        assert len(facts) > 0


class TestStatisticsExtractor:
    def test_extract(self):
        from knowledge_graph.statistics_extractor import StatisticsExtractor
        extractor = StatisticsExtractor()
        stats = extractor.extract(SAMPLE_TRANSCRIPT)
        assert len(stats) > 0
        values = [s.value for s in stats]
        assert "50" in values or "10" in values

    def test_extract_empty(self):
        from knowledge_graph.statistics_extractor import StatisticsExtractor
        extractor = StatisticsExtractor()
        assert extractor.extract({}) == []


class TestTimelineBuilder:
    def test_build(self):
        from knowledge_graph.timeline_builder import TimelineBuilder
        builder = TimelineBuilder()
        events = builder.build(SAMPLE_TRANSCRIPT)
        assert len(events) >= 0

    def test_build_empty(self):
        from knowledge_graph.timeline_builder import TimelineBuilder
        builder = TimelineBuilder()
        assert builder.build(None) == []


class TestPainPointDetector:
    def test_detect(self):
        from knowledge_graph.pain_point_detector import PainPointDetector
        detector = PainPointDetector()
        points = detector.detect(None, SAMPLE_ANALYSIS)
        assert len(points) > 0
        assert any("learning" in p.problem for p in points)

    def test_detect_empty(self):
        from knowledge_graph.pain_point_detector import PainPointDetector
        detector = PainPointDetector()
        assert detector.detect(None, {}) == []


class TestSolutionMapper:
    def test_map(self):
        from knowledge_graph.solution_mapper import SolutionMapper
        mapper = SolutionMapper()
        problems = ["Steep learning curve"]
        solutions = mapper.map(SAMPLE_ANALYSIS, problems)
        assert len(solutions) > 0

    def test_map_empty(self):
        from knowledge_graph.solution_mapper import SolutionMapper
        mapper = SolutionMapper()
        assert mapper.map({}, []) == []


class TestQuoteExtractor:
    def test_extract(self):
        from knowledge_graph.quote_extractor import QuoteExtractor
        extractor = QuoteExtractor()
        quotes = extractor.extract(SAMPLE_TRANSCRIPT)
        assert len(quotes) > 0
        assert any("simplicity" in q.text for q in quotes)

    def test_extract_empty(self):
        from knowledge_graph.quote_extractor import QuoteExtractor
        extractor = QuoteExtractor()
        assert extractor.extract(None) == []


class TestDefinitionExtractor:
    def test_extract(self):
        from knowledge_graph.definition_extractor import DefinitionExtractor
        extractor = DefinitionExtractor()
        definitions = extractor.extract(SAMPLE_TRANSCRIPT, None)
        assert len(definitions) > 0

    def test_extract_empty(self):
        from knowledge_graph.definition_extractor import DefinitionExtractor
        extractor = DefinitionExtractor()
        assert extractor.extract(None, None) == []


class TestRelationshipEngine:
    def test_build(self):
        from knowledge_graph.relationship_engine import RelationshipEngine
        from knowledge_graph.knowledge_graph_models import EntityInfo, EntityType
        engine = RelationshipEngine()
        entities = [
            EntityInfo(name="Python", type=EntityType.TECHNOLOGY),
            EntityInfo(name="Data Science", type=EntityType.CONCEPT),
        ]
        rels = engine.build(entities, SAMPLE_ANALYSIS)
        assert len(rels) > 0

    def test_build_empty(self):
        from knowledge_graph.relationship_engine import RelationshipEngine
        engine = RelationshipEngine()
        assert engine.build([], {}) == []


class TestSemanticClusterEngine:
    def test_cluster(self):
        from knowledge_graph.semantic_cluster_engine import SemanticClusterEngine
        from knowledge_graph.knowledge_graph_models import EntityInfo, EntityType, KeywordInfo
        engine = SemanticClusterEngine()
        entities = [EntityInfo(name="Python", type=EntityType.TECHNOLOGY)]
        keywords = [KeywordInfo(keyword="programming", type="primary")]
        clusters = engine.cluster(entities, keywords)
        assert isinstance(clusters, list)

    def test_cluster_empty(self):
        from knowledge_graph.semantic_cluster_engine import SemanticClusterEngine
        engine = SemanticClusterEngine()
        assert engine.cluster([], []) == []


class TestKnowledgeGraphValidator:
    def test_validate_empty(self):
        from knowledge_graph.knowledge_graph_validator import KnowledgeGraphValidator
        from knowledge_graph.knowledge_graph_models import KnowledgeGraph
        validator = KnowledgeGraphValidator()
        kg = KnowledgeGraph()
        issues = validator.validate(kg)
        assert len(issues) > 0

    def test_quality_score(self):
        from knowledge_graph.knowledge_graph_validator import KnowledgeGraphValidator
        from knowledge_graph.knowledge_graph_models import KnowledgeGraph, EntityInfo, EntityType, KeywordInfo
        validator = KnowledgeGraphValidator()
        kg = KnowledgeGraph()
        kg.entities = [EntityInfo(name=f"E{i}", type=EntityType.CONCEPT) for i in range(5)]
        kg.keywords = [KeywordInfo(keyword=f"K{i}", type="primary") for i in range(10)]
        score = validator.compute_quality_score(kg)
        assert 0 <= score <= 100

    def test_deduplicate(self):
        from knowledge_graph.knowledge_graph_validator import KnowledgeGraphValidator
        from knowledge_graph.knowledge_graph_models import KnowledgeGraph, EntityInfo, EntityType
        validator = KnowledgeGraphValidator()
        kg = KnowledgeGraph()
        kg.entities.append(EntityInfo(name="Python", type=EntityType.TECHNOLOGY))
        kg.entities.append(EntityInfo(name="python", type=EntityType.TECHNOLOGY))
        kg = validator.deduplicate(kg)
        assert kg.entity_count() == 1


class TestKnowledgeGraphEngine:
    def test_build_full(self):
        from knowledge_graph.knowledge_graph_engine import KnowledgeGraphEngine
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

    def test_build_minimal(self):
        from knowledge_graph.knowledge_graph_engine import KnowledgeGraphEngine
        engine = KnowledgeGraphEngine()
        kg = engine.build(analysis=SAMPLE_ANALYSIS)
        assert kg.entity_count() > 0

    def test_build_empty(self):
        from knowledge_graph.knowledge_graph_engine import KnowledgeGraphEngine
        engine = KnowledgeGraphEngine()
        kg = engine.build()
        assert kg.entity_count() == 0


class TestKnowledgeGraphService:
    def test_build_and_summary(self):
        from knowledge_graph.knowledge_graph_service import KnowledgeGraphService
        svc = KnowledgeGraphService()
        kg = svc.build(project_id="test123", metadata={"title": "Test"}, transcript=SAMPLE_TRANSCRIPT, analysis=SAMPLE_ANALYSIS)
        summary = svc.summary(kg)
        assert summary["total_entities"] > 0

    def test_validate(self):
        from knowledge_graph.knowledge_graph_service import KnowledgeGraphService
        from knowledge_graph.knowledge_graph_models import KnowledgeGraph
        svc = KnowledgeGraphService()
        kg = KnowledgeGraph()
        issues = svc.validate(kg)
        assert len(issues) > 0

    def test_quality_score(self):
        from knowledge_graph.knowledge_graph_service import KnowledgeGraphService
        from knowledge_graph.knowledge_graph_models import KnowledgeGraph, EntityInfo, EntityType, KeywordInfo
        svc = KnowledgeGraphService()
        kg = KnowledgeGraph()
        kg.entities.append(EntityInfo(name="Test", type=EntityType.CONCEPT))
        kg.keywords.append(KeywordInfo(keyword="test", type="primary"))
        score = svc.quality_score(kg)
        assert score > 0
