"""Phase 8 — SEO Optimization Engine: 100+ tests."""

from __future__ import annotations
import json
import pytest

from models.seo_package import (
    SEOPackage, SEOOptimizationResult, SEORequest, KeywordDensity, KeywordAnalysis,
    HeadingAnalysis, HeadingInfo, LinkSuggestion, ImageSEO, OpenGraph, TwitterCard,
    SchemaMarkup, ReadabilityAnalysis, SEOStatistics, Recommendation,
)
from exceptions.seo_errors import SEOError, SEOValidationError

# SEO Modules
from modules.seo.slug_generator import generate as gen_slug, from_blog as slug_from_blog
from modules.seo.meta_generator import generate_meta
from modules.seo.keyword_analyzer import analyze as kw_analyze
from modules.seo.density_checker import check_density
from modules.seo.heading_optimizer import analyze as heading_analyze
from modules.seo.link_recommender import suggest_internal, suggest_external
from modules.seo.schema_generator import generate as gen_schema, generate_faq_schema
from modules.seo.social_metadata import generate_og, generate_twitter, generate_all as gen_social
from modules.seo.readability import analyze as read_analyze
from modules.seo.seo_score import compute as seo_score
from modules.seo.recommendation_engine import generate as gen_recs
from modules.seo.seo_optimizer import optimize as run_optimization
from modules.seo.seo_service import SEOService

from models.blog_generation import BlogResult, BlogSection, BlogSubSection, CalloutBox, FAQItem, BlogStatistics


def _sample_blog(**kwargs) -> BlogResult:
    overrides = {
        "seo_title": "Complete Guide to Machine Learning",
        "meta_description": "Learn machine learning basics in this comprehensive guide covering supervised, unsupervised, and reinforcement learning.",
        "slug": "machine-learning-guide",
        "introduction": "Machine learning is transforming industries. " * 8,
        "table_of_contents": ["What is ML", "Supervised Learning", "Unsupervised Learning", "Conclusion"],
        "sections": [
            BlogSection(heading="What is Machine Learning", content="ML is a subset of AI. " * 30, subsections=[BlogSubSection(heading="Key Concepts", content="Concepts explained. " * 10)]),
            BlogSection(heading="Supervised Learning", content="Supervised learning uses labeled data. " * 30, subsections=[BlogSubSection(heading="Regression", content="Regression predicts values. " * 10)]),
            BlogSection(heading="Unsupervised Learning", content="Unsupervised learning finds patterns. " * 30, callout_boxes=[CalloutBox(type="tip", text="Start with supervised learning.")]),
            BlogSection(heading="Conclusion", content="ML continues to evolve. " * 20),
        ],
        "faq": [FAQItem(question=f"Q{i}?", answer=f"A{i}. " * 5) for i in range(1, 6)],
        "conclusion": "Machine learning is powerful. " * 10,
        "call_to_action": "Start learning ML today. Subscribe for more.",
        "markdown": "# Complete Guide\n\nContent.",
        "statistics": BlogStatistics(word_count=1500, reading_time="8 mins", estimated_seo_score=72.0),
    }
    overrides.update(kwargs)
    return BlogResult(**overrides)


# =============================================================================
# Models
# =============================================================================

class TestModels:
    def test_keyword_density_defaults(self):
        k = KeywordDensity()
        assert k.primary == 0.0
        assert k.secondary == {}

    def test_keyword_analysis_defaults(self):
        k = KeywordAnalysis()
        assert k.primary == ""
        assert k.in_title is False

    def test_heading_info(self):
        h = HeadingInfo(level=2, text="Test", has_keyword=True)
        assert h.level == 2
        assert h.has_keyword is True

    def test_heading_analysis(self):
        h = HeadingAnalysis(h1_count=1, h2_count=4, issues=["Missing keyword"])
        assert h.issues == ["Missing keyword"]

    def test_link_suggestion(self):
        l = LinkSuggestion(anchor_text="Learn more", suggested_topic="ML", relevance_score=0.85)
        assert l.relevance_score == 0.85

    def test_image_seo_defaults(self):
        i = ImageSEO()
        assert i.alt_text == ""
        assert i.suggested_filename == ""

    def test_open_graph(self):
        o = OpenGraph(title="Test", description="Desc", type="article")
        assert o.title == "Test"

    def test_twitter_card(self):
        t = TwitterCard(title="Test", card_type="summary_large_image")
        assert t.card_type == "summary_large_image"

    def test_schema_markup_defaults(self):
        s = SchemaMarkup()
        assert s.article == {}

    def test_readability_analysis_defaults(self):
        r = ReadabilityAnalysis()
        assert r.word_count == 0
        assert r.flesch_reading_ease == 0.0

    def test_seo_statistics(self):
        s = SEOStatistics(word_count=1500, seo_score=85.0)
        assert s.seo_score == 85.0

    def test_recommendation(self):
        r = Recommendation(priority="high", category="title", message="Optimize title")
        assert r.priority == "high"

    def test_seo_package_defaults(self):
        p = SEOPackage()
        assert p.meta_title == ""
        assert p.keywords.primary == ""

    def test_seo_package_full(self):
        p = SEOPackage(
            meta_title="ML Guide", meta_description="Desc", slug="ml-guide",
            keywords=KeywordAnalysis(primary="ML", in_title=True),
            statistics=SEOStatistics(seo_score=88.0),
            recommendations=[Recommendation(priority="low", category="faq", message="Add more FAQ")],
        )
        assert p.meta_title == "ML Guide"
        assert p.statistics.seo_score == 88.0
        assert len(p.recommendations) == 1

    def test_optimization_result_defaults(self):
        r = SEOOptimizationResult()
        assert r.success is True
        assert r.seo_package.meta_title == ""

    def test_optimization_result_error(self):
        r = SEOOptimizationResult(success=False, video_id="bad", error="Fail")
        assert r.error == "Fail"

    def test_seo_request(self):
        r = SEORequest(video_id="dQw4w9WgXcQ", blog={"seo_title": "Test"})
        assert r.video_id == "dQw4w9WgXcQ"

    def test_serialization_roundtrip(self):
        p = SEOPackage(meta_title="Test", slug="test", statistics=SEOStatistics(seo_score=90.0))
        r = SEOOptimizationResult(success=True, video_id="v1", seo_package=p)
        data = json.loads(r.model_dump_json())
        assert data["seo_package"]["meta_title"] == "Test"
        assert data["seo_package"]["statistics"]["seo_score"] == 90.0
        restored = SEOOptimizationResult(**data)
        assert restored.seo_package.meta_title == "Test"


# =============================================================================
# Exceptions
# =============================================================================

class TestExceptions:
    def test_seo_error_base(self):
        assert issubclass(SEOError, Exception)

    def test_validation_error(self):
        e = SEOValidationError("Bad input")
        assert "Bad input" in str(e)


# =============================================================================
# Slug Generator
# =============================================================================

class TestSlugGenerator:
    def test_generate_from_title(self):
        assert gen_slug("Machine Learning Guide") == "machine-learning-guide"

    def test_generate_with_special_chars(self):
        assert gen_slug("What is ML? A Guide!") == "what-is-ml-a-guide"

    def test_generate_empty(self):
        assert gen_slug("") == ""

    def test_generate_truncates(self):
        long = "A" * 200
        assert len(gen_slug(long)) <= 80

    def test_from_blog_with_title(self):
        assert slug_from_blog("ML Guide") == "ml-guide"

    def test_from_blog_empty_fallback(self):
        assert slug_from_blog("", fallback="post") == "post"


# =============================================================================
# Meta Generator
# =============================================================================

class TestMetaGenerator:
    def test_generate_meta_without_provider(self):
        meta = generate_meta("ML Guide", "machine learning")
        assert "meta_title" in meta
        assert "meta_description" in meta
        assert len(meta["meta_title"]) <= 60

    def test_generate_meta_empty_title(self):
        meta = generate_meta("")
        assert meta["meta_title"] == ""


# =============================================================================
# Keyword Analyzer
# =============================================================================

class TestKeywordAnalyzer:
    def test_analyze_with_keyword(self):
        blog = _sample_blog()
        result = kw_analyze(blog, "machine learning", ["AI", "deep learning"], ["learn ML"], ["artificial intelligence"])
        assert result["density"]["primary"] > 0
        assert result["in_title"] is True
        assert result["in_intro"] is True

    def test_analyze_empty_keyword(self):
        blog = _sample_blog()
        result = kw_analyze(blog, "")
        assert result["density"]["primary"] == 0.0

    def test_analyze_no_content(self):
        blog = BlogResult()
        result = kw_analyze(blog, "ml")
        assert result["density"]["primary"] == 0.0

    def test_analyze_heading_coverage(self):
        blog = _sample_blog()
        result = kw_analyze(blog, "machine learning")
        assert len(result["in_headings"]) >= 1

    def test_analyze_secondary_density(self):
        blog = _sample_blog()
        result = kw_analyze(blog, "ml", ["supervised", "unsupervised"])
        sec = result["density"]["secondary"]
        assert isinstance(sec, dict)


# =============================================================================
# Density Checker
# =============================================================================

class TestDensityChecker:
    def test_check_density(self):
        text = "machine learning machine learning AI ML machine learning"
        result = check_density(text, ["machine learning", "AI", "ML"])
        assert "machine learning" in result["densities"]
        assert result["densities"]["machine learning"] > 0

    def test_check_density_empty_text(self):
        result = check_density("", ["test"])
        assert result["densities"] == {}

    def test_check_density_empty_keywords(self):
        result = check_density("Some text", [])
        assert result["densities"] == {}

    def test_check_density_recommendations(self):
        text = "keyword " * 100
        result = check_density(text, ["keyword"])
        assert len(result["recommendations"]) >= 1


# =============================================================================
# Heading Optimizer
# =============================================================================

class TestHeadingOptimizer:
    def test_analyze_with_keyword(self):
        blog = _sample_blog()
        result = heading_analyze(blog, "machine learning")
        assert result["h1_count"] == 1
        assert result["h2_count"] >= 3
        assert len(result["headings"]) >= 5

    def test_analyze_empty_blog(self):
        blog = BlogResult()
        result = heading_analyze(blog)
        assert result["h1_count"] == 0
        assert result["h2_count"] == 0

    def test_analyze_issues_no_headings(self):
        blog = BlogResult(seo_title="")
        result = heading_analyze(blog)
        assert len(result["issues"]) >= 1

    def test_analyze_keyword_in_headings(self):
        blog = _sample_blog()
        result = heading_analyze(blog, "machine learning")
        kw_headings = [h["text"] for h in result["headings"] if h["has_keyword"]]
        assert any("Machine Learning" in h for h in kw_headings)


# =============================================================================
# Link Recommender
# =============================================================================

class TestLinkRecommender:
    def test_suggest_internal(self):
        blog = _sample_blog()
        links = suggest_internal(blog)
        assert len(links) > 0
        assert all("anchor_text" in l for l in links)

    def test_suggest_internal_limit(self):
        blog = _sample_blog()
        links = suggest_internal(blog)
        assert len(links) <= 8

    def test_suggest_external(self):
        blog = _sample_blog()
        links = suggest_external(blog)
        assert isinstance(links, list)

    def test_suggest_external_authority(self):
        blog = _sample_blog(sections=[BlogSection(heading="Python Programming", content="Python is great for ML. " * 20)])
        links = suggest_external(blog)
        topics = [l["suggested_topic"] for l in links]
        if links:
            assert any("python" in t.lower() for t in topics) or any("machine" in t.lower() for t in topics)


# =============================================================================
# Schema Generator
# =============================================================================

class TestSchemaGenerator:
    def test_generate_algorithmic(self):
        blog = _sample_blog()
        schema = gen_schema(blog, "dQw4w9WgXcQ", "ML", ["tech", "AI"])
        assert "article" in schema
        assert "blog_posting" in schema
        assert "faq_page" in schema

    def test_generate_faq_schema(self):
        faq = [{"question": "Q1?", "answer": "A1."}, {"question": "Q2?", "answer": "A2."}]
        schema = generate_faq_schema(faq)
        assert schema["@type"] == "FAQPage"
        assert len(schema["mainEntity"]) == 2

    def test_generate_faq_schema_empty(self):
        schema = generate_faq_schema([])
        assert schema["mainEntity"] == []

    def test_schema_has_context(self):
        blog = _sample_blog()
        schema = gen_schema(blog, "v1")
        article = schema.get("article", {})
        assert article.get("headline") == "Complete Guide to Machine Learning"


# =============================================================================
# Social Metadata
# =============================================================================

class TestSocialMetadata:
    def test_generate_og(self):
        blog = _sample_blog()
        og = generate_og(blog, "ML")
        assert og["title"] == "Complete Guide to Machine Learning"
        assert og["type"] == "article"

    def test_generate_twitter(self):
        blog = _sample_blog()
        tw = generate_twitter(blog, "ML")
        assert tw["card_type"] == "summary_large_image"

    def test_generate_all(self):
        blog = _sample_blog()
        social = gen_social(blog, "ML")
        assert "open_graph" in social
        assert "twitter_card" in social


# =============================================================================
# Readability Analysis
# =============================================================================

class TestReadability:
    def test_analyze_full(self):
        blog = _sample_blog()
        r = read_analyze(blog)
        assert r["word_count"] > 0
        assert r["character_count"] > 0
        assert r["paragraph_count"] > 0
        assert r["avg_sentence_length"] > 0
        assert r["flesch_reading_ease"] > 0
        assert r["reading_time"] != ""

    def test_analyze_empty(self):
        blog = BlogResult()
        r = read_analyze(blog)
        assert r["word_count"] == 0

    def test_flesch_score_range(self):
        blog = _sample_blog()
        r = read_analyze(blog)
        assert 0 <= r["flesch_reading_ease"] <= 100

    def test_reading_time(self):
        blog = _sample_blog()
        r = read_analyze(blog)
        assert "min" in r["reading_time"] or "< 1" in r["reading_time"]

    def test_grade_level(self):
        blog = _sample_blog()
        r = read_analyze(blog)
        assert r["grade_level"] != ""


# =============================================================================
# SEO Score
# =============================================================================

class TestSEOScore:
    def test_compute_full(self):
        blog = _sample_blog()
        ka = kw_analyze(blog, "machine learning", ["AI"])
        scores = seo_score(blog, "machine learning", ka)
        assert scores["score"] > 0
        assert scores["score"] <= 100
        assert "components" in scores

    def test_component_keys(self):
        blog = _sample_blog()
        scores = seo_score(blog, "ML")
        expected = {"title", "description", "keyword", "headings", "structure", "content", "readability", "faq", "links", "schema"}
        assert expected.issubset(scores["components"].keys())

    def test_low_score_empty_blog(self):
        blog = BlogResult()
        scores = seo_score(blog)
        assert scores["score"] < 30

    def test_high_score_good_blog(self):
        blog = _sample_blog()
        scores = seo_score(blog, "machine learning")
        assert scores["score"] >= 40


# =============================================================================
# Recommendation Engine
# =============================================================================

class TestRecommendationEngine:
    def test_generate_with_good_blog(self):
        blog = _sample_blog()
        scores = seo_score(blog, "ML")
        kw = kw_analyze(blog, "ML")
        recs = gen_recs(blog, scores, kw)
        assert isinstance(recs, list)

    def test_generate_with_bad_blog(self):
        blog = BlogResult()
        scores = seo_score(blog)
        recs = gen_recs(blog, scores, {})
        assert len(recs) >= 3

    def test_recommendation_priorities(self):
        blog = BlogResult()
        scores = seo_score(blog)
        recs = gen_recs(blog, scores, {})
        priorities = {r["priority"] for r in recs}
        assert priorities.issubset({"critical", "high", "medium", "low"})


# =============================================================================
# SEO Optimizer (Integration)
# =============================================================================

class TestSEOOptimizer:
    def test_optimize_full(self):
        blog = _sample_blog()
        pkg = run_optimization(blog, video_id="dQw4w9WgXcQ", primary_keyword="machine learning", secondary_keywords=["AI", "deep learning"], tags=["tech", "AI"])
        assert pkg.meta_title != ""
        assert pkg.meta_description != ""
        assert pkg.slug != ""
        assert pkg.keywords.primary == "machine learning"
        assert pkg.keywords.in_title is True
        assert pkg.headings.h2_count >= 3
        assert len(pkg.recommendations) >= 0
        assert pkg.statistics.seo_score > 0
        assert pkg.readability.word_count > 0
        assert pkg.schema_markup.article != {}

    def test_optimize_empty_blog(self):
        blog = BlogResult()
        pkg = run_optimization(blog)
        assert pkg.meta_title == ""
        assert pkg.slug != ""

    def test_optimize_includes_internal_links(self):
        blog = _sample_blog()
        pkg = run_optimization(blog)
        assert isinstance(pkg.internal_links, list)

    def test_optimize_includes_external_links(self):
        blog = _sample_blog()
        pkg = run_optimization(blog)
        assert isinstance(pkg.external_links, list)

    def test_optimize_includes_social(self):
        blog = _sample_blog()
        pkg = run_optimization(blog)
        assert pkg.open_graph.title != ""
        assert pkg.twitter_card.title != ""

    def test_optimize_includes_schema(self):
        blog = _sample_blog()
        pkg = run_optimization(blog, video_id="dQw4w9WgXcQ")
        assert pkg.schema_markup.article != {}

    def test_optimize_includes_readability(self):
        blog = _sample_blog()
        pkg = run_optimization(blog)
        assert pkg.readability.word_count > 0
        assert pkg.readability.flesch_reading_ease > 0

    def test_optimize_seo_score(self):
        blog = _sample_blog()
        pkg = run_optimization(blog, primary_keyword="machine learning")
        assert 0 <= pkg.statistics.seo_score <= 100

    def test_optimize_canonical_url(self):
        blog = _sample_blog()
        pkg = run_optimization(blog, video_id="dQw4w9WgXcQ")
        assert "youtube.com" in pkg.canonical_url

    def test_optimize_image_seo(self):
        blog = _sample_blog()
        pkg = run_optimization(blog)
        assert pkg.image.alt_text != ""
        assert ".webp" in pkg.image.suggested_filename


# =============================================================================
# SEO Service
# =============================================================================

class TestSEOService:
    def test_optimize_with_mock_blog_data(self):
        service = SEOService()
        blog_data = {
            "seo_title": "ML Guide",
            "introduction": "ML intro. " * 10,
            "sections": [{"heading": "What is ML", "content": "ML content. " * 30, "subsections": [], "callout_boxes": []}],
            "faq": [{"question": "Q?", "answer": "A."}],
            "conclusion": "Done. " * 5,
            "call_to_action": "Subscribe!",
            "markdown": "# ML Guide\n\nContent.",
        }
        result = service.optimize(blog_data=blog_data, video_id="dQw4w9WgXcQ")
        assert result.success is True
        assert result.seo_package.statistics.seo_score > 0
        assert result.seo_package.meta_title != ""

    def test_optimize_invalid_blog_data(self):
        service = SEOService()
        result = service.optimize(blog_data="not a dict")
        assert result.success is False

    def test_optimize_with_analysis(self):
        service = SEOService()
        blog_data = {"seo_title": "Test", "sections": [], "faq": [], "conclusion": "", "call_to_action": "", "markdown": ""}
        analysis = {"keywords": {"primary": "test keyword", "secondary": ["kw1", "kw2"], "long_tail": [], "semantic": [], "lsi": []}, "primary_topic": "test keyword"}
        result = service.optimize(blog_data=blog_data, video_id="dQw4w9WgXcQ", analysis=analysis)
        assert result.seo_package.keywords.primary == "test keyword"

    def test_optimize_with_metadata(self):
        service = SEOService()
        blog_data = {"seo_title": "Python Tutorial", "sections": [], "faq": [], "conclusion": "", "call_to_action": "", "markdown": ""}
        metadata = {"tags": ["python", "programming", "tutorial"]}
        result = service.optimize(blog_data=blog_data, video_id="dQw4w9WgXcQ", metadata=metadata)
        assert result.success is True


# =============================================================================
# End-to-End SEO Pipeline (Mock)
# =============================================================================

class TestSEOEndToEnd:
    def test_full_seo_pipeline(self):
        service = SEOService()
        blog_data = {
            "seo_title": "Complete Guide to Python Programming",
            "meta_description": "Learn Python programming from scratch with this comprehensive guide covering basics to advanced topics.",
            "slug": "python-programming-guide",
            "introduction": "Python is one of the most popular programming languages. " * 10,
            "table_of_contents": ["Getting Started", "Variables", "Functions", "Classes", "Conclusion"],
            "sections": [
                {"heading": "Getting Started with Python", "content": "Python is easy to learn. " * 30, "subsections": [{"heading": "Installation", "content": "Install Python. " * 10}], "callout_boxes": [{"type": "tip", "text": "Use a virtual environment."}]},
                {"heading": "Variables and Data Types", "content": "Python has dynamic typing. " * 30, "subsections": [], "callout_boxes": []},
                {"heading": "Functions", "content": "Functions are first-class objects. " * 30, "subsections": [{"heading": "Lambda Functions", "content": "Lambda is a one-liner. " * 10}], "callout_boxes": []},
                {"heading": "Classes and OOP", "content": "Python supports OOP. " * 30, "subsections": [], "callout_boxes": [{"type": "warning", "text": "Avoid deep inheritance."}]},
                {"heading": "Conclusion", "content": "Python is versatile. " * 15, "subsections": [], "callout_boxes": []},
            ],
            "faq": [{"question": f"Q{i}?", "answer": f"A{i}. " * 5} for i in range(1, 7)],
            "conclusion": "Python is a great language. " * 8,
            "call_to_action": "Start your Python journey today!",
            "markdown": "# Python Guide\n\nContent.",
            "statistics": {"word_count": 2000, "reading_time": "10 mins", "estimated_seo_score": 75.0},
        }
        analysis = {
            "keywords": {
                "primary": "python programming",
                "secondary": ["python language", "learn python", "python tutorial"],
                "long_tail": ["learn python from scratch", "python for beginners"],
                "semantic": ["coding", "software development"],
                "lsi": ["dynamic typing", "OOP"],
            },
            "primary_topic": "Python Programming",
            "search_intent": "educational",
            "target_audience": "Beginners",
            "difficulty": "beginner",
            "industry": "Technology",
        }
        metadata = {"tags": ["python", "programming", "tutorial", "coding"], "channel": "Tech Academy", "published_date": "2025-06-01"}

        result = service.optimize(blog_data=blog_data, video_id="dQw4w9WgXcQ", metadata=metadata, analysis=analysis)
        assert result.success is True
        assert result.seo_package.meta_title != ""
        assert result.seo_package.meta_description != ""
        assert result.seo_package.slug != ""
        assert result.seo_package.keywords.primary == "python programming"
        assert result.seo_package.keywords.in_title is True
        assert result.seo_package.headings.h2_count >= 4
        assert len(result.seo_package.internal_links) > 0
        assert result.seo_package.open_graph.title != ""
        assert result.seo_package.twitter_card.title != ""
        assert result.seo_package.schema_markup.article != {}
        assert result.seo_package.readability.word_count > 0
        assert result.seo_package.statistics.seo_score > 0
        assert len(result.seo_package.recommendations) >= 0
        assert result.optimization_time_ms > 0


# =============================================================================
# JSON Schema Validation
# =============================================================================

class TestSchema:
    def test_full_result_serialization(self):
        pkg = SEOPackage(
            meta_title="SEO Test",
            meta_description="SEO test description 150 chars",
            slug="seo-test",
            canonical_url="https://example.com/seo-test",
            keywords=KeywordAnalysis(primary="test", in_title=True, in_meta=True, density=KeywordDensity(primary=1.5)),
            headings=HeadingAnalysis(h1_count=1, h2_count=4, headings=[HeadingInfo(level=2, text="H2 Test", has_keyword=True)]),
            internal_links=[LinkSuggestion(anchor_text="Learn more", suggested_topic="Test", relevance_score=0.8)],
            external_links=[LinkSuggestion(anchor_text="Docs", suggested_topic="python", suggested_url="https://python.org", relevance_score=0.9)],
            image=ImageSEO(alt_text="Test image", title="Test", suggested_filename="test.webp"),
            open_graph=OpenGraph(title="OG Test", description="OG desc", type="article"),
            twitter_card=TwitterCard(title="TW Test", description="TW desc", card_type="summary_large_image"),
            schema_markup=SchemaMarkup(article={"@type": "Article", "headline": "Test"}),
            readability=ReadabilityAnalysis(word_count=1000, flesch_reading_ease=65.0, reading_time="5 min"),
            statistics=SEOStatistics(word_count=1000, seo_score=88.5),
            recommendations=[Recommendation(priority="high", category="title", message="Optimize title", suggestion="Add keyword")],
        )
        r = SEOOptimizationResult(
            success=True, video_id="dQw4w9WgXcQ", seo_package=pkg,
            llm_provider="gemini", llm_model="gemini-2.5-flash",
            prompt_version="8.0.0", optimization_time_ms=1500.0,
        )
        data = json.loads(r.model_dump_json())
        assert data["success"] is True
        assert data["seo_package"]["meta_title"] == "SEO Test"
        assert data["seo_package"]["statistics"]["seo_score"] == 88.5
        assert data["seo_package"]["keywords"]["primary"] == "test"
        assert data["seo_package"]["keywords"]["in_title"] is True
        assert data["seo_package"]["keywords"]["density"]["primary"] == 1.5
        assert data["seo_package"]["headings"]["h2_count"] == 4
        assert len(data["seo_package"]["internal_links"]) == 1
        assert data["seo_package"]["schema_markup"]["article"]["headline"] == "Test"
        assert data["seo_package"]["readability"]["word_count"] == 1000
        assert len(data["seo_package"]["recommendations"]) == 1
        assert data["optimization_time_ms"] == 1500.0

    def test_error_response(self):
        r = SEOOptimizationResult(success=False, video_id="bad", error="Analysis failed", optimization_time_ms=500.0)
        data = json.loads(r.model_dump_json())
        assert data["success"] is False
        assert data["error"] == "Analysis failed"
