from __future__ import annotations

import pytest

SAMPLE_KG = {
    "topics": {"name": "Python Programming for Data Science"},
    "entities": [
        {"name": "Python", "type": "technology", "importance_score": 1.0},
        {"name": "Pandas", "type": "library", "importance_score": 0.9},
    ],
    "keywords": [
        {"keyword": "python", "type": "primary", "relevance_score": 1.0},
        {"keyword": "data science", "type": "primary", "relevance_score": 0.9},
    ],
    "facts": [{"statement": "Python is a high-level programming language.", "category": "definition"}],
    "definitions": [{"term": "Python", "definition": "A high-level programming language"}],
    "pain_points": [{"problem": "Steep learning curve", "severity": "high"}],
}

SAMPLE_ANALYSIS = {
    "primary_topic": "Python Programming for Data Science",
    "secondary_topics": ["Machine Learning", "Data Visualization"],
    "search_intent": "educational",
    "content_category": "programming",
    "target_audience": "Data Scientists",
    "experience_level": "intermediate",
    "summary": {"short": "A comprehensive guide", "key_insights": ["Python is popular"]},
    "keywords": {
        "primary": ["Python programming", "data science"],
        "secondary": ["machine learning", "data analysis"],
        "long_tail": ["Python for beginners"],
    },
    "entities": {"technologies": ["Python", "Pandas"], "frameworks": ["Django"]},
}


class TestSEOModels:
    def test_default_plan(self):
        from seo_intelligence.seo_models import SEOPlan
        plan = SEOPlan()
        assert plan.keyword_strategy.primary_keyword == ""
        assert plan.meta.meta_title == ""
        assert plan.scores.overall_score == 0.0

    def test_keyword_strategy(self):
        from seo_intelligence.seo_models import KeywordStrategy
        ks = KeywordStrategy(primary_keyword="Python")
        assert ks.primary_keyword == "Python"

    def test_enums(self):
        from seo_intelligence.seo_models import SearchIntentType, KeywordType, SchemaType
        assert SearchIntentType.INFORMATIONAL.value == "informational"
        assert KeywordType.PRIMARY.value == "primary"
        assert SchemaType.ARTICLE.value == "Article"


class TestKeywordEngine:
    def test_generate(self):
        from seo_intelligence.keyword_engine import KeywordEngine
        engine = KeywordEngine()
        strategy = engine.generate(SAMPLE_KG, SAMPLE_ANALYSIS)
        assert strategy.primary_keyword == "Python Programming for Data Science"
        assert strategy.total_keyword_count > 0

    def test_generate_empty(self):
        from seo_intelligence.keyword_engine import KeywordEngine
        engine = KeywordEngine()
        strategy = engine.generate({}, {})
        assert strategy.primary_keyword == ""


class TestIntentEngine:
    def test_determine(self):
        from seo_intelligence.intent_engine import IntentEngine
        from seo_intelligence.seo_models import SearchIntentType
        engine = IntentEngine()
        intent = engine.determine(SAMPLE_ANALYSIS, "Python")
        assert intent.primary_intent == SearchIntentType.EDUCATIONAL
        assert intent.confidence >= 0.5

    def test_determine_empty(self):
        from seo_intelligence.intent_engine import IntentEngine
        engine = IntentEngine()
        intent = engine.determine({}, "")
        assert intent.primary_intent.value == "informational"


class TestAudienceEngine:
    def test_identify(self):
        from seo_intelligence.audience_engine import AudienceEngine
        engine = AudienceEngine()
        audience = engine.identify(SAMPLE_ANALYSIS, SAMPLE_KG)
        assert audience.primary_audience == "Data Scientists"

    def test_identify_empty(self):
        from seo_intelligence.audience_engine import AudienceEngine
        engine = AudienceEngine()
        audience = engine.identify({}, {})
        assert audience.primary_audience == "General Audience"


class TestURLGenerator:
    def test_generate(self):
        from seo_intelligence.url_generator import URLGenerator
        gen = URLGenerator()
        url = gen.generate("Python Programming for Data Science")
        assert url.suggested_slug
        assert "python" in url.suggested_slug.lower()

    def test_generate_empty(self):
        from seo_intelligence.url_generator import URLGenerator
        gen = URLGenerator()
        url = gen.generate("")
        assert url.suggested_slug


class TestMetaGenerator:
    def test_generate(self):
        from seo_intelligence.meta_generator import MetaGenerator
        from seo_intelligence.seo_models import SearchIntentType
        gen = MetaGenerator()
        meta = gen.generate("Python Programming", SearchIntentType.EDUCATIONAL, "Data Scientists", SAMPLE_ANALYSIS)
        assert meta.meta_title
        assert "Python" in meta.meta_title

    def test_title_length(self):
        from seo_intelligence.meta_generator import MetaGenerator
        from seo_intelligence.seo_models import SearchIntentType
        gen = MetaGenerator()
        meta = gen.generate("Python Programming", SearchIntentType.INFORMATIONAL)
        assert len(meta.meta_title) <= 60


class TestHeadingStrategyEngine:
    def test_generate(self):
        from seo_intelligence.heading_strategy_engine import HeadingStrategyEngine
        engine = HeadingStrategyEngine()
        strategy, content = engine.generate("Python Programming", ["machine learning", "data analysis"], SAMPLE_KG)
        assert strategy.h1 == "Python Programming"
        assert len(strategy.h2_suggestions) > 0


class TestFAQEngine:
    def test_generate(self):
        from seo_intelligence.faq_engine import FAQEngine
        engine = FAQEngine()
        faqs = engine.generate(SAMPLE_KG, "Python")
        assert len(faqs) > 0
        questions = [f.question for f in faqs]
        assert any("Python" in q for q in questions)

    def test_generate_empty(self):
        from seo_intelligence.faq_engine import FAQEngine
        engine = FAQEngine()
        assert engine.generate({}, "") == []


class TestSchemaEngine:
    def test_generate(self):
        from seo_intelligence.schema_engine import SchemaEngine
        from seo_intelligence.seo_models import SchemaType
        engine = SchemaEngine()
        schemas = engine.generate("Python", "Python Guide", "Learn Python", SAMPLE_ANALYSIS)
        assert len(schemas) >= 3
        types = [s.type for s in schemas]
        assert SchemaType.ARTICLE in types

    def test_generate_defaults(self):
        from seo_intelligence.schema_engine import SchemaEngine
        engine = SchemaEngine()
        schemas = engine.generate()
        assert len(schemas) >= 3


class TestFeaturedSnippetEngine:
    def test_generate(self):
        from seo_intelligence.featured_snippet_engine import FeaturedSnippetEngine
        engine = FeaturedSnippetEngine()
        snippets = engine.generate("Python", ["What is Python?"], [{"term": "Python", "definition": "A language"}])
        assert len(snippets) > 0
        assert any("Python" in s.target_question for s in snippets)


class TestCompetitorStrategyEngine:
    def test_generate(self):
        from seo_intelligence.competitor_strategy_engine import CompetitorStrategyEngine
        engine = CompetitorStrategyEngine()
        strategy = engine.generate("Python", SAMPLE_KG, SAMPLE_ANALYSIS)
        assert strategy.content_angle
        assert strategy.unique_value_proposition

    def test_generate_empty(self):
        from seo_intelligence.competitor_strategy_engine import CompetitorStrategyEngine
        engine = CompetitorStrategyEngine()
        strategy = engine.generate()
        assert strategy.content_angle == ""


class TestInternalLinkEngine:
    def test_generate(self):
        from seo_intelligence.internal_link_engine import InternalLinkEngine
        engine = InternalLinkEngine()
        links = engine.generate(SAMPLE_KG, "Python")
        assert isinstance(links, list)


class TestExternalLinkEngine:
    def test_generate(self):
        from seo_intelligence.external_link_engine import ExternalLinkEngine
        engine = ExternalLinkEngine()
        links = engine.generate(SAMPLE_KG, "Python")
        assert len(links) > 0

    def test_generate_empty(self):
        from seo_intelligence.external_link_engine import ExternalLinkEngine
        engine = ExternalLinkEngine()
        assert len(engine.generate({})) == 1


class TestSEOScoring:
    def test_compute(self):
        from seo_intelligence.seo_scoring import SEOScoring
        from seo_intelligence.seo_models import KeywordStrategy, ContentStrategy, KeywordInfo, KeywordType
        scorer = SEOScoring()
        kw_strategy = KeywordStrategy(
            primary_keyword="Python",
            secondary_keywords=[KeywordInfo(keyword="data science", type=KeywordType.SECONDARY) for _ in range(5)],
            lsi_keywords=["coding", "statistics"],
            long_tail_keywords=["Python for beginners"],
        )
        content = ContentStrategy(recommended_word_count=2500, recommended_headings=8)
        score = scorer.compute(kw_strategy, content)
        assert score.overall_score > 0
        assert score.keyword_score > 0

    def test_compute_empty(self):
        from seo_intelligence.seo_scoring import SEOScoring
        from seo_intelligence.seo_models import KeywordStrategy, ContentStrategy
        scorer = SEOScoring()
        score = scorer.compute(KeywordStrategy(), ContentStrategy())
        assert score.overall_score == 0.0


class TestSEOValidator:
    def test_validate_empty(self):
        from seo_intelligence.seo_validator import SEOValidator
        from seo_intelligence.seo_models import SEOPlan
        validator = SEOValidator()
        plan = SEOPlan()
        issues = validator.validate(plan)
        assert len(issues) > 0

    def test_validate_populated(self):
        from seo_intelligence.seo_validator import SEOValidator
        from seo_intelligence.seo_models import SEOPlan, KeywordInfo, KeywordType, HeadingSuggestion, FAQItem, SchemaMarkup, SchemaType
        validator = SEOValidator()
        plan = SEOPlan()
        plan.keyword_strategy.primary_keyword = "Python"
        plan.keyword_strategy.secondary_keywords = [KeywordInfo(keyword="ds", type=KeywordType.SECONDARY) for _ in range(5)]
        plan.url.suggested_slug = "python-guide"
        plan.meta.meta_title = "Python Guide"
        plan.meta.meta_description = "A" * 140
        plan.heading_strategy.h1 = "Python Guide"
        plan.heading_strategy.h2_suggestions = [HeadingSuggestion(tag="h2", text=f"H2 {i}", order=i) for i in range(5)]
        plan.faqs = [FAQItem(question=f"Q{i}", answer="A") for i in range(3)]
        plan.schemas = [SchemaMarkup(type=SchemaType.ARTICLE)]
        plan.content_strategy.recommended_word_count = 1500
        issues = validator.validate(plan)
        assert all("No" not in i for i in issues)


class TestSEOEngine:
    def test_build_full(self):
        from seo_intelligence.seo_engine import SEOEngine
        engine = SEOEngine()
        plan = engine.build(knowledge_graph=SAMPLE_KG, analysis=SAMPLE_ANALYSIS, project_id="test123")
        assert plan.keyword_strategy.primary_keyword == "Python Programming for Data Science"
        assert plan.url.suggested_slug
        assert plan.meta.meta_title
        assert plan.scores.overall_score > 0

    def test_build_minimal(self):
        from seo_intelligence.seo_engine import SEOEngine
        engine = SEOEngine()
        plan = engine.build(analysis=SAMPLE_ANALYSIS)
        assert plan.keyword_strategy.primary_keyword

    def test_build_empty(self):
        from seo_intelligence.seo_engine import SEOEngine
        engine = SEOEngine()
        plan = engine.build()
        assert plan.keyword_strategy.primary_keyword == ""


class TestSEOService:
    def test_build_and_summary(self):
        from seo_intelligence.seo_service import SEOService
        svc = SEOService()
        plan = svc.build(project_id="test123", knowledge_graph=SAMPLE_KG, analysis=SAMPLE_ANALYSIS)
        summary = svc.summary(plan)
        assert summary["primary_keyword"]
        assert summary["overall_seo_score"] > 0

    def test_validate(self):
        from seo_intelligence.seo_service import SEOService
        from seo_intelligence.seo_models import SEOPlan
        svc = SEOService()
        plan = SEOPlan()
        issues = svc.validate(plan)
        assert len(issues) > 0
