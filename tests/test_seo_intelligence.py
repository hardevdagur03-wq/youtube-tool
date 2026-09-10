"""Tests for the SEO Intelligence Engine.

All existing tests continue to work unchanged.
"""

from __future__ import annotations

from seo_intelligence.seo_models import (
    SEOPlan, KeywordStrategy, SearchIntent, TargetAudience,
    MetaInfo, URLInfo, HeadingStrategy, FAQItem,
    SchemaMarkup, SchemaType, FeaturedSnippetPlan,
    InternalLink, ExternalLink, CompetitorStrategy,
    SEOScore, ContentStrategy, ContentDepth, PlanMetadata,
    SearchIntentType, KeywordType, CompetitionLevel, KeywordInfo,
    HeadingSuggestion,
)
from seo_intelligence.keyword_engine import KeywordEngine
from seo_intelligence.intent_engine import IntentEngine
from seo_intelligence.audience_engine import AudienceEngine
from seo_intelligence.url_generator import URLGenerator
from seo_intelligence.meta_generator import MetaGenerator
from seo_intelligence.heading_strategy_engine import HeadingStrategyEngine
from seo_intelligence.faq_engine import FAQEngine
from seo_intelligence.schema_engine import SchemaEngine
from seo_intelligence.featured_snippet_engine import FeaturedSnippetEngine
from seo_intelligence.competitor_strategy_engine import CompetitorStrategyEngine
from seo_intelligence.internal_link_engine import InternalLinkEngine
from seo_intelligence.external_link_engine import ExternalLinkEngine
from seo_intelligence.seo_scoring import SEOScoring
from seo_intelligence.seo_validator import SEOValidator
from seo_intelligence.seo_engine import SEOEngine
from seo_intelligence.seo_service import SEOService

SAMPLE_KG = {
    "topics": {"name": "Python Programming for Data Science"},
    "entities": [
        {"name": "Python", "type": "technology", "importance_score": 1.0},
        {"name": "Pandas", "type": "library", "importance_score": 0.9},
        {"name": "NumPy", "type": "library", "importance_score": 0.8},
        {"name": "Guido van Rossum", "type": "person", "importance_score": 0.5},
    ],
    "keywords": [
        {"keyword": "python", "type": "primary", "relevance_score": 1.0},
        {"keyword": "data science", "type": "primary", "relevance_score": 0.9},
    ],
    "facts": [
        {"statement": "Python is a high-level programming language.", "category": "definition"},
        {"statement": "What is Python used for?", "category": "question"},
    ],
    "definitions": [
        {"term": "Python", "definition": "A high-level programming language"},
        {"term": "API", "definition": "Application Programming Interface"},
    ],
    "semantic_clusters": [
        {"name": "technology", "entities": ["Python", "Pandas"], "keywords": ["programming", "code"]},
        {"name": "data", "entities": ["NumPy"], "keywords": ["data", "analytics"]},
    ],
    "pain_points": [
        {"problem": "Steep learning curve for beginners", "severity": "high"},
    ],
    "solutions": [
        {"problem": "Steep learning curve", "solution": "Start with tutorials"},
    ],
}

SAMPLE_ANALYSIS = {
    "primary_topic": "Python Programming for Data Science",
    "secondary_topics": ["Machine Learning", "Data Visualization"],
    "search_intent": "educational",
    "content_category": "programming",
    "target_audience": "Data Scientists",
    "experience_level": "intermediate",
    "summary": {
        "short": "A comprehensive guide to Python for data science",
        "key_insights": ["Python is popular", "Pandas is essential"],
    },
    "keywords": {
        "primary": ["Python programming", "data science"],
        "secondary": ["machine learning", "data analysis", "Python libraries"],
        "long_tail": ["Python for beginners", "data science tutorial"],
        "semantic": ["programming", "analytics"],
        "lsi": ["coding", "statistics", "visualization"],
    },
    "entities": {
        "technologies": ["Python", "Pandas", "NumPy"],
        "frameworks": ["Django"],
        "tools": ["Jupyter"],
    },
}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TestSEOModels:
    def test_default_plan(self):
        plan = SEOPlan()
        assert plan.keyword_strategy.primary_keyword == ""
        assert plan.meta.meta_title == ""
        assert plan.scores.overall_score == 0.0

    def test_keyword_strategy(self):
        ks = KeywordStrategy(primary_keyword="Python")
        assert ks.primary_keyword == "Python"
        assert ks.total_keyword_count == 0

    def test_search_intent(self):
        si = SearchIntent(primary_intent=SearchIntentType.EDUCATIONAL)
        assert si.primary_intent == SearchIntentType.EDUCATIONAL

    def test_target_audience(self):
        ta = TargetAudience(primary_audience="Data Scientists", skill_level="advanced")
        assert ta.primary_audience == "Data Scientists"

    def test_url_info(self):
        url = URLInfo(suggested_slug="python-guide", keyword_included=True)
        assert url.suggested_slug == "python-guide"

    def test_meta_info(self):
        m = MetaInfo(meta_title="Python Guide", meta_description="Learn Python")
        assert m.meta_title == "Python Guide"

    def test_heading_strategy(self):
        hs = HeadingStrategy(h1="Python Guide")
        assert hs.h1 == "Python Guide"

    def test_heading_suggestion(self):
        h = HeadingSuggestion(tag="h2", text="What is Python?", order=1)
        assert h.text == "What is Python?"

    def test_faq_item(self):
        f = FAQItem(question="What is Python?", answer="A language")
        assert f.question == "What is Python?"

    def test_schema_markup(self):
        s = SchemaMarkup(type=SchemaType.ARTICLE)
        assert s.type == SchemaType.ARTICLE

    def test_featured_snippet(self):
        fs = FeaturedSnippetPlan(target_question="What is Python?", priority=10)
        assert fs.priority == 10

    def test_internal_link(self):
        il = InternalLink(target_topic="Python", relevance_score=0.9)
        assert il.target_topic == "Python"

    def test_external_link(self):
        el = ExternalLink(suggested_domain="python.org", authority_score=0.8)
        assert el.authority_score == 0.8

    def test_competitor_strategy(self):
        cs = CompetitorStrategy(content_angle="Comprehensive guide")
        assert cs.content_angle == "Comprehensive guide"

    def test_seo_score(self):
        s = SEOScore(overall_score=85.0)
        assert s.overall_score == 85.0

    def test_content_strategy(self):
        cs = ContentStrategy(content_depth=ContentDepth.COMPREHENSIVE)
        assert cs.content_depth == ContentDepth.COMPREHENSIVE

    def test_summary(self):
        plan = SEOPlan()
        plan.keyword_strategy.primary_keyword = "Python"
        s = plan.summary
        assert s["primary_keyword"] == "Python"

    def test_plan_metadata(self):
        pm = PlanMetadata(project_id="test123")
        assert pm.project_id == "test123"

    def test_keyword_info(self):
        ki = KeywordInfo(keyword="Python", type=KeywordType.PRIMARY)
        assert ki.type == KeywordType.PRIMARY

    def test_enums(self):
        assert SearchIntentType.INFORMATIONAL.value == "informational"
        assert CompetitionLevel.HIGH.value == "high"
        assert SchemaType.FAQ.value == "FAQPage"
        assert ContentDepth.ULTIMATE.value == "ultimate"


# ---------------------------------------------------------------------------
# Keyword Engine
# ---------------------------------------------------------------------------


class TestKeywordEngine:
    def test_generate(self):
        engine = KeywordEngine()
        strategy = engine.generate(SAMPLE_KG, SAMPLE_ANALYSIS)
        assert strategy.primary_keyword == "Python Programming for Data Science"
        assert strategy.total_keyword_count > 0
        assert len(strategy.secondary_keywords) > 0

    def test_empty(self):
        engine = KeywordEngine()
        strategy = engine.generate({}, {})
        assert strategy.primary_keyword == ""


# ---------------------------------------------------------------------------
# Intent Engine
# ---------------------------------------------------------------------------


class TestIntentEngine:
    def test_determine(self):
        engine = IntentEngine()
        intent = engine.determine(SAMPLE_ANALYSIS, "Python")
        assert intent.primary_intent == SearchIntentType.EDUCATIONAL
        assert intent.confidence >= 0.5

    def test_empty(self):
        engine = IntentEngine()
        intent = engine.determine({}, "")
        assert intent.primary_intent == SearchIntentType.INFORMATIONAL


# ---------------------------------------------------------------------------
# Audience Engine
# ---------------------------------------------------------------------------


class TestAudienceEngine:
    def test_identify(self):
        engine = AudienceEngine()
        audience = engine.identify(SAMPLE_ANALYSIS, SAMPLE_KG)
        assert audience.primary_audience == "Data Scientists"

    def test_empty(self):
        engine = AudienceEngine()
        audience = engine.identify({}, {})
        assert audience.primary_audience == "General Audience"


# ---------------------------------------------------------------------------
# URL Generator
# ---------------------------------------------------------------------------


class TestURLGenerator:
    def test_generate(self):
        gen = URLGenerator()
        url = gen.generate("Python Programming for Data Science")
        assert url.suggested_slug
        assert url.length > 0
        assert "python" in url.suggested_slug
        assert url.suggested_slug.islower()

    def test_empty_keyword(self):
        gen = URLGenerator()
        url = gen.generate("", "My Blog Post Title")
        assert url.suggested_slug


# ---------------------------------------------------------------------------
# Meta Generator
# ---------------------------------------------------------------------------


class TestMetaGenerator:
    def test_generate(self):
        gen = MetaGenerator()
        meta = gen.generate("Python Programming", SearchIntentType.EDUCATIONAL, "Data Scientists", SAMPLE_ANALYSIS)
        assert meta.meta_title
        assert meta.meta_description
        assert "Python" in meta.meta_title

    def test_title_length(self):
        gen = MetaGenerator()
        meta = gen.generate("Python Programming", SearchIntentType.INFORMATIONAL)
        assert len(meta.meta_title) <= 60


# ---------------------------------------------------------------------------
# Heading Strategy
# ---------------------------------------------------------------------------


class TestHeadingStrategy:
    def test_generate(self):
        engine = HeadingStrategyEngine()
        strategy, content = engine.generate(
            "Python Programming",
            ["machine learning", "data analysis", "Python libraries"],
            SAMPLE_KG,
        )
        assert strategy.h1 == "Python Programming"
        assert len(strategy.h2_suggestions) > 0
        assert content.recommended_word_count > 0


# ---------------------------------------------------------------------------
# FAQ Engine
# ---------------------------------------------------------------------------


class TestFAQEngine:
    def test_generate(self):
        engine = FAQEngine()
        faqs = engine.generate(SAMPLE_KG, "Python")
        assert len(faqs) > 0
        questions = [f.question for f in faqs]
        assert any("Python" in q for q in questions)

    def test_empty(self):
        engine = FAQEngine()
        assert engine.generate({}, "") == []


# ---------------------------------------------------------------------------
# Schema Engine
# ---------------------------------------------------------------------------


class TestSchemaEngine:
    def test_generate(self):
        engine = SchemaEngine()
        schemas = engine.generate("Python", "Python Guide", "Learn Python", SAMPLE_ANALYSIS)
        assert len(schemas) >= 3
        types = [s.type for s in schemas]
        assert SchemaType.ARTICLE in types

    def test_defaults(self):
        engine = SchemaEngine()
        schemas = engine.generate()
        assert len(schemas) >= 3


# ---------------------------------------------------------------------------
# Featured Snippet Engine
# ---------------------------------------------------------------------------


class TestFeaturedSnippetEngine:
    def test_generate(self):
        engine = FeaturedSnippetEngine()
        snippets = engine.generate("Python", ["What is Python?"], [{"term": "Python", "definition": "A language"}])
        assert len(snippets) > 0
        assert any("Python" in s.target_question for s in snippets)

    def test_empty(self):
        engine = FeaturedSnippetEngine()
        snippets = engine.generate("")
        assert isinstance(snippets, list)


# ---------------------------------------------------------------------------
# Competitor Strategy
# ---------------------------------------------------------------------------


class TestCompetitorStrategy:
    def test_generate(self):
        engine = CompetitorStrategyEngine()
        strategy = engine.generate("Python", SAMPLE_KG, SAMPLE_ANALYSIS)
        assert strategy.content_angle
        assert strategy.unique_value_proposition

    def test_empty(self):
        engine = CompetitorStrategyEngine()
        strategy = engine.generate()
        assert strategy.content_angle == ""


# ---------------------------------------------------------------------------
# Internal Link Engine
# ---------------------------------------------------------------------------


class TestInternalLinkEngine:
    def test_generate(self):
        engine = InternalLinkEngine()
        links = engine.generate(SAMPLE_KG, "Python")
        assert len(links) > 0

    def test_empty(self):
        engine = InternalLinkEngine()
        assert engine.generate({}) == []


# ---------------------------------------------------------------------------
# External Link Engine
# ---------------------------------------------------------------------------


class TestExternalLinkEngine:
    def test_generate(self):
        engine = ExternalLinkEngine()
        links = engine.generate(SAMPLE_KG, "Python")
        assert len(links) > 0

    def test_empty(self):
        engine = ExternalLinkEngine()
        assert len(engine.generate({})) == 1  # fallback


# ---------------------------------------------------------------------------
# SEO Scoring
# ---------------------------------------------------------------------------


class TestSEOScoring:
    def test_compute(self):
        scorer = SEOScoring()
        kw_strategy = KeywordStrategy(
            primary_keyword="Python",
            secondary_keywords=[
                KeywordInfo(keyword="data science", type=KeywordType.SECONDARY),
                KeywordInfo(keyword="machine learning", type=KeywordType.SECONDARY),
                KeywordInfo(keyword="data analysis", type=KeywordType.SECONDARY),
                KeywordInfo(keyword="Python libraries", type=KeywordType.SECONDARY),
                KeywordInfo(keyword="coding", type=KeywordType.SECONDARY),
            ],
            lsi_keywords=["coding", "statistics", "visualization"],
            long_tail_keywords=["Python for beginners"],
            question_keywords=["What is Python?"],
            entity_keywords=["Python", "Pandas", "NumPy"],
        )
        content = ContentStrategy(recommended_word_count=2500, recommended_headings=8, recommended_examples=3, recommended_statistics=2)
        score = scorer.compute(kw_strategy, content)
        assert score.overall_score > 0
        assert score.keyword_score > 0

    def test_empty(self):
        scorer = SEOScoring()
        score = scorer.compute(KeywordStrategy(), ContentStrategy())
        assert score.overall_score == 0.0


# ---------------------------------------------------------------------------
# SEO Validator
# ---------------------------------------------------------------------------


class TestSEOValidator:
    def test_validate_empty(self):
        validator = SEOValidator()
        plan = SEOPlan()
        issues = validator.validate(plan)
        assert len(issues) > 0

    def test_validate_populated(self):
        validator = SEOValidator()
        plan = SEOPlan()
        plan.keyword_strategy.primary_keyword = "Python"
        plan.keyword_strategy.secondary_keywords = [
            KeywordInfo(keyword="ds", type=KeywordType.SECONDARY) for _ in range(5)
        ]
        plan.url.suggested_slug = "python-guide"
        plan.meta.meta_title = "Python Programming Guide"
        plan.meta.meta_description = "A" * 140
        plan.heading_strategy.h1 = "Python Guide"
        plan.heading_strategy.h2_suggestions = [HeadingSuggestion(tag="h2", text=f"H2 {i}", order=i) for i in range(5)]
        plan.faqs = [FAQItem(question=f"Q{i}", answer="A") for i in range(3)]
        plan.schemas = [SchemaMarkup(type=SchemaType.ARTICLE)]
        plan.content_strategy.recommended_word_count = 1500
        issues = validator.validate(plan)
        assert all("No" not in i for i in issues)


# ---------------------------------------------------------------------------
# SEO Engine (Integration)
# ---------------------------------------------------------------------------


class TestSEOEngine:
    def test_build_full(self):
        engine = SEOEngine()
        plan = engine.build(
            knowledge_graph=SAMPLE_KG,
            analysis=SAMPLE_ANALYSIS,
            metadata={"title": "Test"},
            project_id="test123",
            video_id="vid123",
        )
        assert plan.keyword_strategy.primary_keyword == "Python Programming for Data Science"
        assert len(plan.keyword_strategy.secondary_keywords) > 0
        assert plan.url.suggested_slug
        assert plan.meta.meta_title
        assert len(plan.heading_strategy.h2_suggestions) > 0
        assert len(plan.faqs) > 0
        assert len(plan.schemas) > 0
        assert plan.scores.overall_score > 0
        assert plan.metadata.execution_time_ms >= 0

    def test_build_minimal(self):
        engine = SEOEngine()
        plan = engine.build(analysis=SAMPLE_ANALYSIS)
        assert plan.keyword_strategy.primary_keyword

    def test_build_empty(self):
        engine = SEOEngine()
        plan = engine.build()
        assert plan.keyword_strategy.primary_keyword == ""


# ---------------------------------------------------------------------------
# SEO Service
# ---------------------------------------------------------------------------


class TestSEOService:
    def test_build_and_summary(self):
        svc = SEOService()
        plan = svc.build(
            project_id="test123",
            knowledge_graph=SAMPLE_KG,
            analysis=SAMPLE_ANALYSIS,
        )
        summary = svc.summary(plan)
        assert summary["primary_keyword"]
        assert summary["overall_seo_score"] > 0

    def test_validate(self):
        svc = SEOService()
        plan = SEOPlan()
        issues = svc.validate(plan)
        assert len(issues) > 0
