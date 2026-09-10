"""Tests for Phase 6 — AI Content Analysis Engine."""

import json
import pytest
from datetime import datetime, timezone

from models.content_analysis import (
    ContentAnalysisResult,
    ContentAnalysisResult,
    AnalysisSummary,
    KeywordSet,
    EntitySet,
    ContentOutline,
    QualityScores,
    SearchIntent,
    ContentCategory,
    ContentType,
    DifficultyLevel,
)
from exceptions.analysis_errors import (
    AnalysisError,
    LLMProviderError,
    LLMAuthenticationError,
    LLMRateLimitError,
    InvalidTranscriptError,
)
from providers.llm_provider import (
    MockProvider,
    OpenAIProvider,
    ProviderConfig,
    LLMResponse,
    create_provider,
    estimate_cost,
)
from utils.prompt_builder import build_analysis_prompt, get_system_prompt, get_prompt_version
from utils.token_counter import estimate_tokens
from utils.confidence import compute_confidence, compute_depth_score
from repositories.analysis_repository import AnalysisRepository
from services.content_analysis_service import ContentAnalysisService


# =========================================================================
# Models
# =========================================================================

class TestContentAnalysisModels:
    def test_content_analysis_result_defaults(self):
        r = ContentAnalysisResult(video_id="dQw4w9WgXcQ")
        assert r.success is True
        assert r.video_id == "dQw4w9WgXcQ"
        assert r.primary_topic == ""
        assert r.category == ContentCategory.OTHER
        assert r.search_intent == SearchIntent.INFORMATIONAL
        assert r.quality.confidence == 0.0

    def test_content_analysis_result_full(self):
        r = ContentAnalysisResult(
            success=True,
            video_id="dQw4w9WgXcQ",
            primary_topic="Machine Learning Basics",
            secondary_topics=["Neural Networks", "Deep Learning"],
            category=ContentCategory.AI,
            search_intent=SearchIntent.EDUCATIONAL,
            intent_confidence=0.95,
            summary=AnalysisSummary(short="A video about ML", bullet_points=["Point 1"]),
            keywords=KeywordSet(primary="machine learning", secondary=["AI", "ML"]),
            entities=EntitySet(people=["Andrew Ng"], technologies=["TensorFlow"]),
            outline=ContentOutline(sections=["Intro", "Core Concepts", "Conclusion"]),
            quality=QualityScores(depth_score=85, seo_potential=78, confidence=0.92),
        )
        assert r.primary_topic == "Machine Learning Basics"
        assert r.category.value == "ai"
        assert r.search_intent.value == "educational"
        assert r.summary.short == "A video about ML"
        assert r.keywords.primary == "machine learning"
        assert "Andrew Ng" in r.entities.people
        assert len(r.outline.sections) == 3
        assert r.quality.depth_score == 85.0
        assert r.quality.confidence == 0.92

    def test_content_analysis_result_error(self):
        r = ContentAnalysisResult(success=False, video_id="bad", error="LLM unavailable")
        assert r.success is False
        assert r.error == "LLM unavailable"

    def test_analysis_summary_defaults(self):
        s = AnalysisSummary()
        assert s.short == ""
        assert s.bullet_points == []

    def test_keyword_set_defaults(self):
        k = KeywordSet()
        assert k.primary == ""
        assert k.secondary == []

    def test_entity_set_defaults(self):
        e = EntitySet()
        assert e.people == []
        assert e.companies == []

    def test_content_outline_defaults(self):
        o = ContentOutline()
        assert o.sections == []

    def test_quality_scores_defaults(self):
        q = QualityScores()
        assert q.depth_score == 0.0
        assert q.confidence == 0.0

    def test_serialization_roundtrip(self):
        r = ContentAnalysisResult(
            video_id="dQw4w9WgXcQ",
            primary_topic="Test Topic",
            quality=QualityScores(depth_score=90, seo_potential=80, confidence=0.95),
        )
        data = json.loads(r.model_dump_json())
        assert data["primary_topic"] == "Test Topic"
        assert data["quality"]["depth_score"] == 90.0
        assert data["quality"]["confidence"] == 0.95

        restored = ContentAnalysisResult(**data)
        assert restored.primary_topic == "Test Topic"


# =========================================================================
# Exceptions
# =========================================================================

class TestAnalysisExceptions:
    def test_base_exception(self):
        assert issubclass(AnalysisError, Exception)

    def test_llm_auth_error(self):
        exc = LLMAuthenticationError("Invalid API key")
        assert "Invalid API key" in str(exc)

    def test_llm_rate_limit(self):
        exc = LLMRateLimitError("Rate limited")
        assert str(exc) == "Rate limited"

    def test_invalid_transcript(self):
        exc = InvalidTranscriptError("Empty transcript")
        assert str(exc) == "Empty transcript"


# =========================================================================
# LLM Providers
# =========================================================================

class TestMockProvider:
    def test_provider_name(self):
        p = MockProvider()
        assert p.provider_name == "mock"

    def test_generate_returns_response(self):
        p = MockProvider()
        resp = p.generate("Test prompt about machine learning")
        assert isinstance(resp, LLMResponse)
        assert resp.provider == "mock"
        assert resp.latency_ms >= 0
        assert resp.cost_estimate == 0.0

    def test_generate_json_returns_dict(self):
        p = MockProvider()
        result = p.generate_json("Analyze this transcript about Python programming")
        assert isinstance(result, dict)
        assert "primary_topic" in result
        assert "keywords" in result
        assert "entities" in result
        assert "outline" in result
        assert "quality" in result

    def test_mock_response_has_expected_structure(self):
        p = MockProvider()
        result = p.generate_json("Video about artificial intelligence and deep learning")
        assert result["primary_topic"] != ""
        assert isinstance(result["secondary_topics"], list)
        assert isinstance(result["keywords"]["secondary"], list)
        assert isinstance(result["entities"]["people"], list)
        assert isinstance(result["outline"]["sections"], list)
        assert len(result["outline"]["sections"]) > 0
        assert isinstance(result["quality"]["depth_score"], (int, float))


class TestProviderFactory:
    def test_create_openai_with_sk_key(self):
        config = ProviderConfig(api_key="sk-test123", model="gpt-4o-mini")
        provider = create_provider(config)
        assert provider.provider_name == "openai"

    def test_create_gemini_with_plain_key(self):
        config = ProviderConfig(api_key="AIzaSyTestGeminiKey123", model="gemini-1.5-flash")
        provider = create_provider(config)
        assert provider.provider_name == "gemini"

    def test_create_gemini_with_extra_hint(self):
        config = ProviderConfig(api_key="any-key", extra={"provider": "gemini"})
        provider = create_provider(config)
        assert provider.provider_name == "gemini"

    def test_create_mock_without_key(self):
        config = ProviderConfig(api_key="", model="mock-v1")
        provider = create_provider(config)
        assert provider.provider_name == "mock"

    def test_estimate_cost(self):
        cost = estimate_cost("gpt-4o-mini", 1000, 500)
        assert cost > 0

    def test_gemini_cost_estimate(self):
        cost = estimate_cost("gemini-1.5-flash", 1000, 500)
        assert cost > 0


# =========================================================================
# Prompt Builder
# =========================================================================

class TestPromptBuilder:
    def test_build_analysis_prompt(self):
        prompt = build_analysis_prompt(
            transcript="Hello world test transcript.",
            video_id="dQw4w9WgXcQ",
            categories="technology",
            language="en",
        )
        assert "Hello world test transcript" in prompt
        assert "dQw4w9WgXcQ" in prompt
        assert "technology" in prompt
        assert "primary_topic" in prompt
        assert "keywords" in prompt

    def test_build_prompt_truncates_long_transcripts(self):
        long_text = "word " * 50000
        prompt = build_analysis_prompt(
            transcript=long_text,
            video_id="test12345678",
        )
        assert len(prompt) < 100000  # truncated

    def test_system_prompt(self):
        sp = get_system_prompt()
        assert "JSON" in sp
        assert "structured" in sp

    def test_prompt_version(self):
        v = get_prompt_version()
        assert v == "1.0.0"


# =========================================================================
# Token Counter
# =========================================================================

class TestTokenCounter:
    def test_estimate_tokens_empty(self):
        assert estimate_tokens("") == 1

    def test_estimate_tokens(self):
        tokens = estimate_tokens("Hello world this is a test")
        assert tokens > 0


# =========================================================================
# Confidence
# =========================================================================

class TestConfidence:
    def test_compute_confidence_high(self):
        c = compute_confidence(
            word_count=1000,
            sentence_count=50,
            has_entities=True,
            has_keywords=True,
            has_outline=True,
        )
        assert c >= 0.5
        assert c <= 1.0

    def test_compute_confidence_low(self):
        c = compute_confidence(
            word_count=10,
            sentence_count=2,
            has_entities=False,
            has_keywords=False,
            has_outline=False,
        )
        assert c < 0.5

    def test_depth_score(self):
        d = compute_depth_score(word_count=2000, entity_count=10, keyword_count=15, outline_sections=5)
        assert d > 0
        assert d <= 100.0


# =========================================================================
# Analysis Repository
# =========================================================================

class TestAnalysisRepository:
    def test_save_and_get(self):
        repo = AnalysisRepository()
        result = ContentAnalysisResult(
            success=True,
            video_id="dQw4w9WgXcQ",
            primary_topic="Test Topic",
        )
        repo.save("dQw4w9WgXcQ", result)
        cached = repo.get("dQw4w9WgXcQ")
        assert cached is not None
        assert cached.primary_topic == "Test Topic"

    def test_get_missing(self):
        repo = AnalysisRepository()
        assert repo.get("nonexistent") is None

    def test_delete(self):
        repo = AnalysisRepository()
        result = ContentAnalysisResult(video_id="test12345678")
        repo.save("test12345678", result)
        assert repo.delete("test12345678") is True
        assert repo.get("test12345678") is None

    def test_clear(self):
        repo = AnalysisRepository()
        result = ContentAnalysisResult(video_id="test12345678")
        repo.save("test12345678", result)
        repo.clear()
        assert repo.get("test12345678") is None

    def test_cached_video_ids(self):
        repo = AnalysisRepository()
        repo.save("video1", ContentAnalysisResult(video_id="video1"))
        repo.save("video2", ContentAnalysisResult(video_id="video2"))
        ids = repo.get_cached_video_ids()
        assert "video1" in ids
        assert "video2" in ids


# =========================================================================
# Content Analysis Service
# =========================================================================

class TestContentAnalysisService:
    def test_analyze_with_mock_provider(self):
        provider = MockProvider()
        service = ContentAnalysisService(provider=provider)
        result = service.analyze(
            transcript="This is a video about artificial intelligence and machine learning. "
                       "We discuss neural networks and deep learning algorithms. "
                       "The video covers Python programming for AI applications.",
            video_id="dQw4w9WgXcQ",
        )
        assert result.success is True
        assert result.video_id == "dQw4w9WgXcQ"
        assert result.primary_topic != ""
        assert result.analysis_time_ms >= 0
        assert result.llm_provider == "mock"

    def test_analyze_invalid_video_id(self):
        service = ContentAnalysisService(provider=MockProvider())
        result = service.analyze(
            transcript="Test transcript here.",
            video_id="bad",
        )
        assert result.success is False
        assert result.error is not None

    def test_analyze_empty_transcript(self):
        service = ContentAnalysisService(provider=MockProvider())
        result = service.analyze(
            transcript="",
            video_id="dQw4w9WgXcQ",
        )
        assert result.success is False

    def test_analyze_returns_structured_data(self):
        provider = MockProvider()
        service = ContentAnalysisService(provider=provider)
        result = service.analyze(
            transcript="Introduction to Python programming for beginners. "
                       "We cover variables, loops, and functions. "
                       "This is a great starting point for learning to code.",
            video_id="dQw4w9WgXcQ",
        )
        assert result.primary_topic != ""
        assert isinstance(result.secondary_topics, list)
        assert isinstance(result.keywords, KeywordSet)
        assert isinstance(result.entities, EntitySet)
        assert isinstance(result.outline, ContentOutline)
        assert isinstance(result.quality, QualityScores)
        assert isinstance(result.summary, AnalysisSummary)
        assert isinstance(result.search_intent, SearchIntent)
        assert isinstance(result.category, ContentCategory)
        assert result.summary.short != "" or result.summary.bullet_points != []

    def test_analyze_caches_result(self):
        repo = AnalysisRepository()
        service = ContentAnalysisService(
            provider=MockProvider(),
            repository=repo,
        )
        result1 = service.analyze(
            transcript="Some video content about technology.",
            video_id="dQw4w9WgXcQ",
        )
        cached = repo.get("dQw4w9WgXcQ")
        assert cached is not None
        assert cached.primary_topic == result1.primary_topic

    def test_analyze_bypasses_cache_with_force_refresh(self):
        repo = AnalysisRepository()
        service = ContentAnalysisService(
            provider=MockProvider(),
            repository=repo,
        )
        result1 = service.analyze(
            transcript="First transcript about AI.",
            video_id="video12345678",
        )
        result2 = service.analyze(
            transcript="Second transcript about ML.",
            video_id="video12345678",
            force_refresh=True,
        )
        assert result2.video_id == "video12345678"

    def test_create_default_provider_with_gemini_key(self):
        import os
        from config.settings import settings
        orig_env = os.environ.get("GEMINI_API_KEY")
        orig_setting = settings.gemini_api_key
        os.environ["GEMINI_API_KEY"] = "AIzaSyTestKey"
        try:
            settings.gemini_api_key = "AIzaSyTestKey"
            from services.content_analysis_service import ContentAnalysisService
            service = ContentAnalysisService()
            assert service._provider.provider_name == "gemini"
        finally:
            if orig_env is not None:
                os.environ["GEMINI_API_KEY"] = orig_env
            else:
                os.environ.pop("GEMINI_API_KEY", None)
            settings.gemini_api_key = orig_setting


# =========================================================================
# Content Analysis Result JSON Schema
# =========================================================================

class TestContentAnalysisJSONSchema:
    def test_json_serialization(self):
        r = ContentAnalysisResult(
            success=True,
            video_id="dQw4w9WgXcQ",
            primary_topic="Test Topic",
            secondary_topics=["Sub Topic"],
            category=ContentCategory.EDUCATION,
            content_type=ContentType.TUTORIAL,
            search_intent=SearchIntent.INFORMATIONAL,
            intent_confidence=0.9,
            target_audience="Developers",
            experience_level=DifficultyLevel.INTERMEDIATE,
            industry="Technology",
            key_takeaways=["Takeaway 1"],
            summary=AnalysisSummary(short="Short", executive="Exec", detailed="Detail"),
            keywords=KeywordSet(primary="test", secondary=["a", "b"]),
            entities=EntitySet(people=["Person"], technologies=["Tech"]),
            outline=ContentOutline(sections=["Intro", "Body", "Conclusion"]),
            quality=QualityScores(depth_score=88, seo_potential=92, confidence=0.96),
            analysis_time_ms=1500.5,
            llm_provider="openai",
            llm_model="gpt-4o-mini",
            prompt_version="1.0.0",
            total_tokens=1500,
            input_tokens=1000,
            output_tokens=500,
            cost_estimate=0.0025,
        )
        data = json.loads(r.model_dump_json())
        assert data["success"] is True
        assert data["primary_topic"] == "Test Topic"
        assert data["category"] == "education"
        assert data["search_intent"] == "informational"
        assert data["quality"]["depth_score"] == 88.0
        assert data["quality"]["seo_potential"] == 92.0
        assert data["quality"]["confidence"] == 0.96
        assert data["keywords"]["primary"] == "test"
        assert data["entities"]["people"] == ["Person"]
        assert len(data["outline"]["sections"]) == 3
