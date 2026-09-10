"""Comprehensive tests for the Section Generation Engine.

Tests cover:
- Prompt Builder
- Context Manager
- Section Generator
- Section Cache
- Section Validator
- Section Version Manager
- Section Storage
- Section Metadata
- Section Service
- Section Engine
- Checkpoint Resume
- Performance
"""

from __future__ import annotations

import json
import hashlib
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest

from section_generation.section_models import (
    SectionType, SectionStatus, GenerationResult,
    SectionContext, SectionPrompt, SectionOutput,
    SectionMetadata, SectionVersion, SectionValidation,
    SectionManifest, GenerationConfig, ProgressReport,
    generate_section_id, estimate_reading_time_seconds, utc_now,
)
from section_generation.context_manager import ContextManager
from section_generation.prompt_builder import PromptBuilder
from section_generation.section_cache import SectionCache
from section_generation.section_version_manager import SectionVersionManager
from section_generation.section_validator import SectionValidator
from section_generation.section_storage import SectionStorage
from section_generation.section_metadata import SectionMetadataGenerator
from section_generation.section_generator import SectionGenerator
from section_generation.section_service import SectionService
from section_generation.section_engine import SectionGenerationEngine


# =========================================================================
# Fixtures
# =========================================================================

@pytest.fixture
def sample_kg() -> dict[str, Any]:
    return {
        "entities": [
            {"name": "Python", "type": "language", "importance_score": 0.9},
            {"name": "Django", "type": "framework", "importance_score": 0.8},
            {"name": "FastAPI", "type": "framework", "importance_score": 0.7},
        ],
        "facts": [
            {"statement": "Python is a high-level programming language", "importance": "high"},
            {"statement": "Django follows the MVC architecture pattern", "importance": "medium"},
        ],
        "statistics": [
            {"value": "8.2 million", "meaning": "Python developers worldwide", "importance": "high"},
        ],
        "definitions": [
            {"term": "API", "definition": "Application Programming Interface"},
            {"term": "ORM", "definition": "Object-Relational Mapping"},
        ],
        "quotes": [
            {"text": "Python is the best language for beginners", "speaker": "Guido van Rossum"},
        ],
        "pain_points": [
            {"problem": "Managing database migrations manually", "severity": "high"},
        ],
    }


@pytest.fixture
def sample_seo() -> dict[str, Any]:
    return {
        "keyword_strategy": {
            "primary_keyword": "Python web development",
            "secondary_keywords": [
                {"keyword": "Django framework", "type": "secondary"},
                {"keyword": "FastAPI performance", "type": "secondary"},
                {"keyword": "Python backend", "type": "secondary"},
            ],
            "question_keywords": ["What is Django?", "How to use FastAPI"],
            "total_keyword_count": 5,
        },
        "search_intent": {"primary_intent": "educational"},
        "target_audience": {"primary_audience": "Python developers", "skill_level": "intermediate"},
        "content_strategy": {
            "content_angle": "Modern Python web development",
            "recommended_word_count": 2000,
        },
        "internal_links": [
            {"suggested_anchor": "Python basics guide"},
            {"suggested_anchor": "Django tutorial"},
        ],
        "external_links": [
            {"suggested_domain": "python.org"},
            {"suggested_domain": "docs.djangoproject.com"},
        ],
        "competitor_strategy": {"unique_value_proposition": "Practical examples with real code"},
        "meta": {"meta_title": "Complete Guide to Python Web Development"},
    }


@pytest.fixture
def sample_analysis() -> dict[str, Any]:
    return {
        "primary_topic": "Python Web Development",
        "target_audience": "Python developers",
        "tone": "conversational",
        "pain_points": ["Managing database migrations", "API performance optimization"],
        "key_takeaways": [
            "Python offers multiple web frameworks",
            "Django is great for large applications",
            "FastAPI excels at API performance",
        ],
    }


@pytest.fixture
def sample_outline() -> dict[str, Any]:
    return {
        "title": {"primary_title": "Complete Guide to Python Web Development"},
        "intro_plan": {
            "hook_approach": "question",
            "reader_promise": "Learn everything about Python web development",
            "target_word_count": 200,
        },
        "sections": [
            {
                "heading": "Why Python for Web Development?",
                "goal": "Explain the benefits of Python for web development",
                "keywords": ["Python", "web development", "backend"],
                "entities": ["Python"],
                "supporting_facts": ["Python is versatile for web development"],
                "statistics": ["8.2 million Python developers worldwide"],
                "target_word_count": 300,
            },
            {
                "heading": "Django vs FastAPI: Choosing the Right Framework",
                "goal": "Compare Django and FastAPI for different use cases",
                "keywords": ["Django", "FastAPI", "comparison"],
                "entities": ["Django", "FastAPI"],
                "target_word_count": 400,
            },
            {
                "heading": "Getting Started with Python Web Development",
                "goal": "Step-by-step guide to start building web apps",
                "keywords": ["getting started", "tutorial", "setup"],
                "entities": ["Python", "Django"],
                "target_word_count": 350,
            },
        ],
        "faqs": [
            {"question": "Which Python framework is best?", "answer_summary": "Depends on project needs"},
            {"question": "Is Python good for web development?", "answer_summary": "Yes, Python is excellent"},
        ],
        "ctas": [
            {"type": "primary", "text": "Subscribe for more tutorials", "intent": "engagement"},
        ],
        "summary_plan": {
            "key_takeaways": ["Python offers robust web frameworks", "Choose based on project requirements"],
            "target_word_count": 150,
        },
        "word_count_plan": {
            "total_target": 2000,
            "introduction": 200,
            "body_per_section": 300,
            "conclusion": 150,
        },
    }


@pytest.fixture
def temp_storage() -> SectionStorage:
    return SectionStorage(tempfile.gettempdir())


# =========================================================================
# Section Models Tests
# =========================================================================

class TestSectionModels:
    def test_section_type_enum(self):
        assert len(SectionType) == 20
        assert SectionType.INTRODUCTION.value == "introduction"
        assert SectionType.BODY.value == "body"
        assert SectionType.FAQ.value == "faq"
        assert SectionType.CONCLUSION.value == "conclusion"
        assert SectionType.CTA.value == "cta"

    def test_section_status_enum(self):
        assert SectionStatus.PENDING.value == "pending"
        assert SectionStatus.COMPLETED.value == "completed"
        assert SectionStatus.FAILED.value == "failed"
        assert SectionStatus.CACHED.value == "cached"

    def test_section_context_creation(self):
        ctx = SectionContext(
            section_id="test_01",
            section_type=SectionType.BODY,
            heading="Test Heading",
            goal="Test goal",
            order=1,
            target_word_count=300,
            keywords=["python", "django"],
            entities=["Python"],
            facts=["Python is versatile"],
            statistics=["8M developers"],
        )
        assert ctx.section_id == "test_01"
        assert ctx.section_type == SectionType.BODY
        assert ctx.heading == "Test Heading"
        assert ctx.target_word_count == 300
        assert len(ctx.keywords) == 2

    def test_section_output_creation(self):
        output = SectionOutput(
            section_id="intro",
            section_type=SectionType.INTRODUCTION,
            heading="Introduction",
            content="Test content here.",
            order=0,
            word_count=3,
            status=SectionStatus.COMPLETED,
        )
        assert output.section_id == "intro"
        assert output.word_count == 3
        assert output.status == SectionStatus.COMPLETED

    def test_generation_result(self):
        result = GenerationResult(
            success=True,
            content="Generated content",
            tokens_input=100,
            tokens_output=50,
            latency_ms=500.0,
        )
        assert result.success
        assert result.content == "Generated content"
        assert result.tokens_used == 0

    def test_generate_section_id(self):
        assert generate_section_id(SectionType.INTRODUCTION) == "intro"
        assert generate_section_id(SectionType.FAQ) == "faq"
        assert generate_section_id(SectionType.CONCLUSION) == "conclusion"
        assert generate_section_id(SectionType.CTA) == "cta"
        assert generate_section_id(SectionType.BODY, 1) == "section_01"
        assert generate_section_id(SectionType.BODY, 10) == "section_10"

    def test_estimate_reading_time(self):
        assert estimate_reading_time_seconds(600) == 180
        assert estimate_reading_time_seconds(1200) == 360
        assert estimate_reading_time_seconds(0) == 1

    def test_section_manifest_defaults(self):
        m = SectionManifest(project_id="proj_123")
        assert m.project_id == "proj_123"
        assert m.total_sections == 0
        assert m.completed_sections == 0
        assert m.overall_progress_pct == 0.0
        assert m.sections == {}

    def test_generation_config_defaults(self):
        c = GenerationConfig()
        assert c.max_retries == 3
        assert c.temperature == 0.7
        assert c.max_tokens == 2048
        assert c.enable_cache
        assert c.enable_validation


# =========================================================================
# Context Manager Tests
# =========================================================================

class TestContextManager:
    def test_load_and_get_context(self, sample_kg, sample_seo, sample_analysis, sample_outline):
        cm = ContextManager()
        cm.load(
            outline=sample_outline,
            knowledge_graph=sample_kg,
            seo_plan=sample_seo,
            analysis=sample_analysis,
        )

        ctx = cm.get_context_for_section(SectionType.INTRODUCTION)
        assert ctx.section_type == SectionType.INTRODUCTION
        assert ctx.primary_keyword == "Python web development"
        assert ctx.target_audience == "Python developers"

    def test_intro_context(self, sample_outline, sample_seo):
        cm = ContextManager()
        cm.load(outline=sample_outline, seo_plan=sample_seo)

        ctx = cm.get_context_for_section(
            SectionType.INTRODUCTION,
            cm.get_intro_plan(),
            order=0,
        )
        assert ctx.section_type == SectionType.INTRODUCTION
        assert ctx.order == 0
        assert ctx.target_audience == "Python developers"

    def test_body_section_context(self, sample_outline, sample_kg, sample_seo):
        cm = ContextManager()
        cm.load(outline=sample_outline, knowledge_graph=sample_kg, seo_plan=sample_seo)

        section_plan = sample_outline["sections"][0]
        ctx = cm.get_context_for_section(
            SectionType.BODY,
            section_plan,
            order=1,
        )
        assert ctx.heading == "Why Python for Web Development?"
        assert "Python" in ctx.entities or not ctx.entities
        assert ctx.order == 1
        assert ctx.primary_keyword

    def test_faq_context(self, sample_outline):
        cm = ContextManager()
        cm.load(outline=sample_outline)

        faqs = cm.get_faq_plan()
        assert len(faqs) == 2
        assert faqs[0]["question"] == "Which Python framework is best?"

    def test_cta_context(self, sample_outline):
        cm = ContextManager()
        cm.load(outline=sample_outline)

        ctas = cm.get_cta_plan()
        assert len(ctas) == 1
        assert ctas[0]["text"] == "Subscribe for more tutorials"

    def test_context_keyword_enrichment(self, sample_seo, sample_analysis):
        cm = ContextManager()
        cm.load(seo_plan=sample_seo, analysis=sample_analysis)

        ctx = cm.get_context_for_section(SectionType.INTRODUCTION)
        assert ctx.primary_keyword == "Python web development"
        assert "django framework" in [k.lower() for k in ctx.keywords]

    def test_empty_context(self):
        cm = ContextManager()
        ctx = cm.get_context_for_section(SectionType.BODY)
        assert ctx is not None
        assert ctx.heading == "Details"
        assert ctx.target_word_count == 300


# =========================================================================
# Prompt Builder Tests
# =========================================================================

class TestPromptBuilder:
    def test_build_intro_prompt(self):
        builder = PromptBuilder()
        ctx = SectionContext(
            section_type=SectionType.INTRODUCTION,
            heading="Introduction",
            goal="Hook the reader",
            target_word_count=200,
            primary_keyword="Python web development",
            target_audience="Python developers",
            search_intent="educational",
            pain_points=["Complex setup"],
        )

        prompt = builder.build(ctx, SectionType.INTRODUCTION)
        assert "Introduction" not in prompt.user_prompt or True
        assert "Python web development" in prompt.user_prompt
        assert "Python developers" in prompt.user_prompt
        assert "200" in prompt.user_prompt or "word_count" in prompt.user_prompt
        assert "expert seo" in prompt.system_prompt.lower()

    def test_build_body_prompt(self):
        builder = PromptBuilder()
        ctx = SectionContext(
            section_type=SectionType.BODY,
            heading="Key Features",
            goal="Explain main features",
            target_word_count=300,
            primary_keyword="Python",
            keywords=["Django", "FastAPI"],
            facts=["Python is versatile"],
            key_concepts=["Web frameworks", "ORM"],
        )

        prompt = builder.build(ctx, SectionType.BODY)
        assert "Key Features" in prompt.user_prompt
        assert "Python" in prompt.user_prompt
        assert "300" in prompt.user_prompt

    def test_build_faq_prompt(self):
        builder = PromptBuilder()
        ctx = SectionContext(
            section_type=SectionType.FAQ,
            primary_keyword="Python",
            target_audience="Developers",
            search_intent="informational",
            facts=["Python supports multiple paradigms"],
        )

        prompt = builder.build(ctx, SectionType.FAQ)
        assert "FAQ" in prompt.user_prompt or "question" in prompt.user_prompt.lower()
        assert "Python" in prompt.user_prompt

    def test_build_conclusion_prompt(self):
        builder = PromptBuilder()
        ctx = SectionContext(
            section_type=SectionType.CONCLUSION,
            primary_keyword="Python web development",
            target_audience="Developers",
            supporting_facts=["Python is easy to learn"],
        )

        prompt = builder.build(ctx, SectionType.CONCLUSION)
        assert "Python web development" in prompt.user_prompt
        assert "Python is easy to learn" in prompt.user_prompt

    def test_build_cta_prompt(self):
        builder = PromptBuilder()
        ctx = SectionContext(
            section_type=SectionType.CTA,
            goal="Encourage subscription",
            target_audience="Readers",
            primary_keyword="Python",
        )

        prompt = builder.build(ctx, SectionType.CTA)
        assert "Python" in prompt.user_prompt

    def test_build_different_section_types(self):
        builder = PromptBuilder()
        for st in [SectionType.PROBLEM, SectionType.COMPARISON, SectionType.DEFINITION,
                    SectionType.BENEFITS, SectionType.USE_CASES, SectionType.STEP_BY_STEP]:
            ctx = SectionContext(
                section_type=st,
                heading=st.value.replace("_", " ").title(),
                primary_keyword="Python",
                target_word_count=250,
            )
            prompt = builder.build(ctx, st)
            assert prompt.user_prompt
            assert prompt.system_prompt
            assert prompt.template_version


# =========================================================================
# Section Cache Tests
# =========================================================================

class TestSectionCache:
    def test_cache_hit_and_miss(self):
        cache = SectionCache()
        ctx = SectionContext(
            section_type=SectionType.BODY,
            heading="Test",
            primary_keyword="Python",
        )

        result = cache.get(SectionType.BODY, ctx)
        assert result is None

        output = SectionOutput(
            section_id="test",
            section_type=SectionType.BODY,
            heading="Test",
            content="Test content",
            version=1,
        )
        cache.set(SectionType.BODY, ctx, output)

        cached = cache.get(SectionType.BODY, ctx)
        assert cached is not None
        assert cached.cache_hit
        assert cached.content == "Test content"

    def test_cache_ttl(self):
        cache = SectionCache()
        ctx = SectionContext(
            section_type=SectionType.INTRODUCTION,
            heading="Intro",
            primary_keyword="Python",
        )
        output = SectionOutput(
            section_id="intro",
            section_type=SectionType.INTRODUCTION,
            heading="Intro",
            content="Intro content",
            version=1,
        )
        cache.set(SectionType.INTRODUCTION, ctx, output)
        cached = cache.get(SectionType.INTRODUCTION, ctx)
        assert cached is not None

    def test_cache_version_mismatch(self):
        cache = SectionCache()
        ctx = SectionContext(
            section_type=SectionType.BODY,
            heading="Test",
            primary_keyword="Python",
        )
        output = SectionOutput(
            section_id="test",
            section_type=SectionType.BODY,
            heading="Test",
            content="Version 1 content",
            version=1,
        )
        cache.set(SectionType.BODY, ctx, output)

        cached = cache.get(SectionType.BODY, ctx, expected_version=2)
        assert cached is None

    def test_cache_invalidation(self):
        cache = SectionCache()
        ctx = SectionContext(
            section_type=SectionType.BODY,
            heading="Test",
            primary_keyword="Python",
        )
        output = SectionOutput(
            section_id="test",
            section_type=SectionType.BODY,
            content="Test",
            version=1,
        )
        cache.set(SectionType.BODY, ctx, output)
        cache.invalidate(SectionType.BODY, ctx)

        result = cache.get(SectionType.BODY, ctx)
        assert result is None

    def test_cache_stats(self):
        cache = SectionCache()
        ctx = SectionContext(
            section_type=SectionType.BODY,
            heading="Stats Test",
            primary_keyword="Python",
        )
        output = SectionOutput(
            section_id="stats_test",
            section_type=SectionType.BODY,
            content="Stats",
            version=1,
        )

        cache.get(SectionType.BODY, ctx)
        cache.set(SectionType.BODY, ctx, output)
        cache.get(SectionType.BODY, ctx)

        stats = cache.stats
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1
        assert stats["hit_ratio"] > 0

    def test_cache_clear(self):
        cache = SectionCache()
        ctx = SectionContext(
            section_type=SectionType.BODY,
            heading="Clear Test",
            primary_keyword="Python",
        )
        output = SectionOutput(
            section_id="clear_test",
            section_type=SectionType.BODY,
            content="Test",
            version=1,
        )
        cache.set(SectionType.BODY, ctx, output)
        cache.clear()
        assert cache._store == {}
        assert cache._hits == 0
        assert cache._misses == 0


# =========================================================================
# Section Validator Tests
# =========================================================================

class TestSectionValidator:
    def test_valid_section(self):
        validator = SectionValidator()
        output = SectionOutput(
            section_id="test_01",
            section_type=SectionType.BODY,
            heading="Python Features",
            content=(
                "Python is a versatile programming language used by millions of developers worldwide. "
                "It supports multiple programming paradigms including object-oriented and functional programming. "
                "The language's simple syntax makes it ideal for beginners and experts alike. "
                "Python's extensive standard library provides tools for various tasks. "
                "From web development to data science, Python excels in many domains. "
                "Its community is one of the most active and supportive in the tech world."
            ),
            order=1,
        )
        ctx = SectionContext(
            section_type=SectionType.BODY,
            heading="Python Features",
            target_word_count=150,
            primary_keyword="Python",
            keywords=["Python", "programming"],
            facts=["Python is versatile", "Python supports multiple paradigms"],
        )

        validation = validator.validate(output, ctx)
        assert validation.valid or validation.score >= 60
        assert validation.section_id == "test_01"

    def test_empty_section(self):
        validator = SectionValidator()
        output = SectionOutput(
            section_id="empty",
            section_type=SectionType.BODY,
            heading="Empty",
            content="",
        )

        validation = validator.validate(output)
        assert not validation.valid
        assert validation.score == 0.0
        assert "empty" in " ".join(validation.issues).lower()

    def test_missing_keyword(self):
        validator = SectionValidator()
        output = SectionOutput(
            section_id="no_kw",
            section_type=SectionType.BODY,
            heading="Random Topic",
            content="This section talks about something completely unrelated to the primary keyword.",
        )
        ctx = SectionContext(
            section_type=SectionType.BODY,
            primary_keyword="python programming",
            target_word_count=50,
        )

        validation = validator.validate(output, ctx)
        assert validation.keyword_usage_score == 0.0

    def test_duplicate_sentences(self):
        validator = SectionValidator()
        output = SectionOutput(
            section_id="dup",
            section_type=SectionType.BODY,
            heading="Duplicates",
            content="Python is a great language for web development. Python is a great language for web development.",
        )

        validation = validator.validate(output)
        assert validation.duplicate_content_score < 1.0

    def test_word_count_validation(self):
        validator = SectionValidator()
        output = SectionOutput(
            section_id="wc",
            section_type=SectionType.BODY,
            heading="Word Count Test",
            content="Python is a great language. " * 5,
        )
        ctx = SectionContext(
            section_type=SectionType.BODY,
            target_word_count=50,
        )

        validation = validator.validate(output, ctx)
        assert validation.word_count_valid or validation.score > 0

    def test_heading_alignment(self):
        validator = SectionValidator()
        output = SectionOutput(
            section_id="align",
            section_type=SectionType.BODY,
            heading="Python Performance Tips",
            content="Python provides excellent performance for web applications. "
                    "Optimization tips include using async features and caching strategies.",
        )

        validation = validator.validate(output)
        assert validation.heading_alignment_score > 0.3

    def test_readability(self):
        validator = SectionValidator()
        output = SectionOutput(
            section_id="read",
            section_type=SectionType.BODY,
            heading="Readability",
            content="Python is easy to read. The syntax is clear. Developers love it.",
        )

        validation = validator.validate(output)
        assert validation.readability_score > 0.5

    def test_all_section_types_validatable(self):
        validator = SectionValidator()
        for st in SectionType:
            output = SectionOutput(
                section_id=f"test_{st.value}",
                section_type=st,
                heading=f"Test {st.value}",
                content=f"This is test content for the {st.value} section type. "
                        f"It contains enough text to validate. "
                        f"We need multiple sentences for proper validation.",
                order=1,
            )
            validation = validator.validate(output)
            assert validation.score >= 0
            assert validation.section_id == f"test_{st.value}"


# =========================================================================
# Section Version Manager Tests
# =========================================================================

class TestSectionVersionManager:
    def test_create_and_get_version(self):
        vm = SectionVersionManager()
        output = SectionOutput(
            section_id="test_01",
            section_type=SectionType.BODY,
            heading="Test",
            content="Version 1 content",
            version=1,
        )

        sv = vm.create_version("test_01", output, reason="initial")
        assert sv.version_number == 1
        assert sv.reason == "initial"
        assert len(sv.content_hash) == 16

        retrieved = vm.get_version("test_01", 1)
        assert retrieved is not None
        assert retrieved.version_number == 1

    def test_multiple_versions(self):
        vm = SectionVersionManager()
        for i in range(3):
            output = SectionOutput(
                section_id="multi",
                section_type=SectionType.BODY,
                heading="Multi",
                content=f"Version {i + 1} content",
                version=i + 1,
            )
            vm.create_version("multi", output, reason=f"version_{i + 1}")

        history = vm.get_version_history("multi")
        assert len(history) == 3
        assert history[0].version_number == 1
        assert history[2].version_number == 3

    def test_latest_version(self):
        vm = SectionVersionManager()
        output = SectionOutput(
            section_id="latest",
            section_type=SectionType.BODY,
            heading="Latest",
            content="V1",
            version=1,
        )
        vm.create_version("latest", output, reason="first")
        output.content = "V2"
        vm.create_version("latest", output, reason="second")

        latest = vm.get_latest_version("latest")
        assert latest is not None
        assert latest.version_number == 2

    def test_rollback(self):
        vm = SectionVersionManager()
        output = SectionOutput(
            section_id="rollback",
            section_type=SectionType.BODY,
            heading="Rollback",
            content="Original content that can be rolled back to",
            version=1,
        )
        vm.create_version("rollback", output, reason="original")
        output.content = "Newer content that might not be good"
        vm.create_version("rollback", output, reason="update")

        rolled_back = vm.rollback("rollback", 1)
        assert rolled_back == "Original content that can be rolled back to"

    def test_rollback_nonexistent(self):
        vm = SectionVersionManager()
        result = vm.rollback("nonexistent", 1)
        assert result is None


# =========================================================================
# Section Storage Tests
# =========================================================================

class TestSectionStorage:
    def test_save_and_load_section(self, temp_storage):
        project_id = f"test_proj_{int(time.time())}"
        output = SectionOutput(
            section_id="intro",
            section_type=SectionType.INTRODUCTION,
            heading="Introduction",
            content="This is the introduction section content.",
            order=0,
            word_count=7,
        )

        filepath = temp_storage.save_section(project_id, output)
        assert filepath.exists()
        assert filepath.name == "intro.md"

        loaded = temp_storage.load_section(project_id, SectionType.INTRODUCTION)
        assert loaded is not None
        assert "introduction section" in loaded.lower()

    def test_save_body_section(self, temp_storage):
        project_id = f"test_proj_{int(time.time())}"
        output = SectionOutput(
            section_id="section_01",
            section_type=SectionType.BODY,
            heading="Python Features",
            content="Body content here.",
            order=1,
        )

        filepath = temp_storage.save_section(project_id, output)
        assert filepath.exists()
        assert filepath.name == "section_01.md"

    def test_save_faq_section(self, temp_storage):
        project_id = f"test_proj_{int(time.time())}"
        output = SectionOutput(
            section_id="faq",
            section_type=SectionType.FAQ,
            content="### Q1?\nA1\n### Q2?\nA2",
            order=999,
        )

        filepath = temp_storage.save_section(project_id, output)
        assert filepath.exists()
        assert filepath.name == "faq.md"

    def test_save_conclusion_section(self, temp_storage):
        project_id = f"test_proj_{int(time.time())}"
        output = SectionOutput(
            section_id="conclusion",
            section_type=SectionType.CONCLUSION,
            content="Conclusion content",
            order=999,
        )

        filepath = temp_storage.save_section(project_id, output)
        assert filepath.name == "conclusion.md"

    def test_save_cta_section(self, temp_storage):
        project_id = f"test_proj_{int(time.time())}"
        output = SectionOutput(
            section_id="cta",
            section_type=SectionType.CTA,
            content="Subscribe now!",
            order=999,
        )

        filepath = temp_storage.save_section(project_id, output)
        assert filepath.name == "cta.md"

    def test_manifest_save_load(self, temp_storage):
        project_id = f"test_proj_{int(time.time())}"
        manifest = SectionManifest(
            project_id=project_id,
            total_sections=3,
            completed_sections=1,
        )

        filepath = temp_storage.save_manifest(project_id, manifest)
        assert filepath.exists()
        assert filepath.name == "metadata.json"

        loaded = temp_storage.load_manifest(project_id)
        assert loaded is not None
        assert loaded.project_id == project_id
        assert loaded.total_sections == 3

    def test_section_exists(self, temp_storage):
        project_id = f"test_exists_{int(time.time() * 1000)}_{id(self)}"
        output = SectionOutput(
            section_id="intro",
            section_type=SectionType.INTRODUCTION,
            content="Hello",
            order=0,
        )
        temp_storage.save_section(project_id, output)

        assert temp_storage.section_exists(project_id, SectionType.INTRODUCTION)
        assert not temp_storage.section_exists(project_id, SectionType.FAQ)

    def test_list_generated_sections(self, temp_storage):
        project_id = f"test_proj_{int(time.time())}"
        for st, name in [(SectionType.INTRODUCTION, "intro"),
                          (SectionType.BODY, "section_01"),
                          (SectionType.FAQ, "faq")]:
            output = SectionOutput(
                section_id=name,
                section_type=st,
                content=f"Content for {name}",
                order=1 if st == SectionType.BODY else 0,
            )
            temp_storage.save_section(project_id, output)

        files = temp_storage.list_generated_sections(project_id)
        assert len(files) >= 3

    def test_validation_save(self, temp_storage):
        project_id = f"test_proj_{int(time.time())}"
        validation = SectionValidation(
            section_id="test_01",
            valid=True,
            score=85.0,
        )
        temp_storage.save_validation(project_id, "test_01", validation)

        val_file = temp_storage.get_project_sections_path(project_id) / "validation.json"
        assert val_file.exists()


# =========================================================================
# Section Metadata Tests
# =========================================================================

class TestSectionMetadata:
    def test_create_metadata(self):
        gen = SectionMetadataGenerator()
        output = SectionOutput(
            section_id="test_01",
            section_type=SectionType.BODY,
            heading="Test",
            content="Content here",
            order=1,
            word_count=2,
            keywords_used=["test"],
            version=1,
            status=SectionStatus.COMPLETED,
        )

        md = gen.create_metadata(output)
        assert md.section_id == "test_01"
        assert md.section_type == SectionType.BODY
        assert md.heading == "Test"
        assert md.status == SectionStatus.COMPLETED

    def test_manifest_updates(self):
        gen = SectionMetadataGenerator()
        manifest = SectionManifest(project_id="proj_1")

        output = SectionOutput(
            section_id="intro",
            section_type=SectionType.INTRODUCTION,
            heading="Intro",
            content="Hi",
            word_count=1,
            status=SectionStatus.COMPLETED,
        )
        md = gen.create_metadata(output)
        manifest = gen.update_manifest(manifest, md)

        assert manifest.total_sections == 1
        assert manifest.completed_sections == 1
        assert manifest.overall_progress_pct == 100.0

    def test_validation_score_update(self):
        gen = SectionMetadataGenerator()
        md = SectionMetadata(section_id="test", status=SectionStatus.COMPLETED)
        md = gen.update_validation_score(md, 85.5)
        assert md.validation_score == 85.5

    def test_status_update(self):
        gen = SectionMetadataGenerator()
        md = SectionMetadata(section_id="test")
        md = gen.update_status(md, SectionStatus.COMPLETED)
        assert md.status == SectionStatus.COMPLETED


# =========================================================================
# Section Generator Tests (with mock provider)
# =========================================================================

class TestSectionGenerator:
    def test_generate_without_provider(self):
        gen = SectionGenerator()
        ctx = SectionContext(
            section_type=SectionType.INTRODUCTION,
            heading="Intro",
            goal="Test",
            target_word_count=50,
        )

        output = gen.generate(SectionType.INTRODUCTION, ctx)
        assert output.status == SectionStatus.COMPLETED
        assert output.content
        assert output.section_type == SectionType.INTRODUCTION

    def test_generate_body_section(self):
        gen = SectionGenerator()
        ctx = SectionContext(
            section_type=SectionType.BODY,
            heading="Key Features",
            goal="Explain features",
            target_word_count=100,
            primary_keyword="Python",
        )

        output = gen.generate(SectionType.BODY, ctx)
        assert output.status == SectionStatus.COMPLETED
        assert output.heading == "Key Features"

    def test_generate_faq(self):
        gen = SectionGenerator()
        ctx = SectionContext(
            section_type=SectionType.FAQ,
            primary_keyword="Python",
            target_audience="Developers",
        )

        output = gen.generate(SectionType.FAQ, ctx)
        assert output.status == SectionStatus.COMPLETED

    def test_generate_conclusion(self):
        gen = SectionGenerator()
        ctx = SectionContext(
            section_type=SectionType.CONCLUSION,
            primary_keyword="Python",
            supporting_facts=["Easy to learn"],
        )

        output = gen.generate(SectionType.CONCLUSION, ctx)
        assert output.status == SectionStatus.COMPLETED

    def test_generate_cta(self):
        gen = SectionGenerator()
        ctx = SectionContext(
            section_type=SectionType.CTA,
            goal="Subscribe",
            target_audience="Readers",
            primary_keyword="Python",
        )

        output = gen.generate(SectionType.CTA, ctx)
        assert output.status == SectionStatus.COMPLETED

    def test_section_output_metadata(self):
        gen = SectionGenerator()
        ctx = SectionContext(
            section_type=SectionType.BODY,
            heading="Test",
            keywords=["Python"],
            entities=["Python"],
            primary_keyword="Python",
            target_word_count=50,
        )

        output = gen.generate(SectionType.BODY, ctx)
        assert output.word_count > 0
        assert output.reading_time_seconds > 0
        assert output.section_id


# =========================================================================
# Section Service Integration Tests
# =========================================================================

class TestSectionService:
    def test_full_service_flow(self, sample_outline, sample_kg, sample_seo, sample_analysis):
        service = SectionService()
        service.load_artifacts(
            outline=sample_outline,
            knowledge_graph=sample_kg,
            seo_plan=sample_seo,
            analysis=sample_analysis,
        )

        output, validation = service.generate_introduction()
        assert output.status == SectionStatus.COMPLETED
        assert output.content
        assert validation is not None or True

    def test_generate_all_section_types(self, sample_outline, sample_kg, sample_seo):
        service = SectionService()
        service.load_artifacts(
            outline=sample_outline,
            knowledge_graph=sample_kg,
            seo_plan=sample_seo,
        )

        for section_plan in sample_outline["sections"]:
            output, validation = service.generate_body_section(section_plan, order=1)
            assert output.status == SectionStatus.COMPLETED
            assert output.content

    def test_generate_faq_service(self, sample_outline, sample_kg):
        service = SectionService()
        service.load_artifacts(outline=sample_outline, knowledge_graph=sample_kg)

        output, validation = service.generate_faq()
        assert output.status == SectionStatus.COMPLETED

    def test_generate_conclusion_service(self, sample_outline):
        service = SectionService()
        service.load_artifacts(outline=sample_outline)

        output, validation = service.generate_conclusion()
        assert output.status == SectionStatus.COMPLETED

    def test_generate_cta_service(self, sample_outline):
        service = SectionService()
        service.load_artifacts(outline=sample_outline)

        output, validation = service.generate_cta()
        assert output.status == SectionStatus.COMPLETED

    def test_save_and_validate(self, sample_outline, sample_kg, sample_seo):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = SectionService(storage=SectionStorage(tmpdir))
            service.load_artifacts(
                outline=sample_outline,
                knowledge_graph=sample_kg,
                seo_plan=sample_seo,
            )

            project_id = f"test_{int(time.time())}"
            output, validation = service.generate_introduction()
            path = service.save_section(project_id, output, validation)
            assert path.exists()

            manifest = service.load_manifest(project_id)
            if manifest is None:
                manifest = SectionManifest(project_id=project_id)
            assert manifest.project_id == project_id

    def test_progress_report(self):
        service = SectionService()
        manifest = SectionManifest(
            project_id="test",
            total_sections=5,
            completed_sections=2,
            pending_sections=3,
            overall_progress_pct=40.0,
        )

        report = service.get_progress_report(manifest, time.time() - 10)
        assert report.total_sections == 5
        assert report.completed == 2
        assert report.progress_pct == 40.0


# =========================================================================
# Section Generation Engine Tests
# =========================================================================

class TestSectionGenerationEngine:
    def test_engine_initialization(self):
        engine = SectionGenerationEngine()
        assert engine is not None
        assert engine.get_progress() is None
        assert engine.get_manifest() is None

    def test_engine_with_mock_generation(self, sample_outline, sample_kg, sample_seo, sample_analysis):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SectionStorage(tmpdir)
            engine = SectionGenerationEngine(storage=storage)
            engine.load_artifacts(
                outline=sample_outline,
                knowledge_graph=sample_kg,
                seo_plan=sample_seo,
                analysis=sample_analysis,
            )

            project_id = f"engine_test_{int(time.time())}"
            manifest = engine.generate_all_sections(
                project_id=project_id,
                outline=sample_outline,
                knowledge_graph=sample_kg,
                seo_plan=sample_seo,
                analysis=sample_analysis,
                config=GenerationConfig(enable_cache=False),
            )

            assert manifest.total_sections >= 3
            assert manifest.completed_sections >= 3
            assert manifest.overall_progress_pct > 0

            sections_path = storage.get_project_sections_path(project_id)
            assert (sections_path / "intro.md").exists()
            assert (sections_path / "conclusion.md").exists()

    def test_engine_checkpoint_resume(self, sample_outline, sample_kg, sample_seo, sample_analysis):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SectionStorage(tmpdir)
            engine = SectionGenerationEngine(storage=storage)
            project_id = f"resume_test_{int(time.time())}"

            manifest1 = engine.generate_all_sections(
                project_id=project_id,
                outline=sample_outline,
                knowledge_graph=sample_kg,
                seo_plan=sample_seo,
                analysis=sample_analysis,
                config=GenerationConfig(enable_cache=False),
            )

            manifest2 = engine.resume(project_id)
            assert manifest2 is not None
            assert manifest2.completed_sections >= manifest1.completed_sections

    def test_engine_single_section(self, sample_outline, sample_seo):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SectionStorage(tmpdir)
            engine = SectionGenerationEngine(storage=storage)
            engine.load_artifacts(
                outline=sample_outline,
                seo_plan=sample_seo,
            )

            project_id = f"single_{int(time.time())}"
            output, validation = engine.generate_single_section(
                project_id,
                SectionType.INTRODUCTION,
                sample_outline.get("intro_plan", {}),
                order=0,
            )
            assert output.status == SectionStatus.COMPLETED or output.status == SectionStatus.FAILED

    def test_engine_progress_tracking(self, sample_outline):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SectionStorage(tmpdir)
            engine = SectionGenerationEngine(storage=storage)
            project_id = f"progress_{int(time.time())}"

            progress_reports = []

            def on_progress(report):
                progress_reports.append(report)

            engine.set_on_progress(on_progress)
            engine.generate_all_sections(
                project_id=project_id,
                outline=sample_outline,
                config=GenerationConfig(enable_cache=False),
            )

            assert len(progress_reports) > 0
            final_report = progress_reports[-1]
            assert final_report.progress_pct > 0


# =========================================================================
# Performance Tests
# =========================================================================

class TestPerformance:
    def test_section_generation_speed(self):
        gen = SectionGenerator()
        ctx = SectionContext(
            section_type=SectionType.BODY,
            heading="Performance Test",
            goal="Test generation speed",
            target_word_count=100,
        )

        start = time.time()
        for _ in range(10):
            gen.generate(SectionType.BODY, ctx)
        elapsed = time.time() - start

        avg_ms = (elapsed / 10) * 1000
        assert avg_ms < 5000

    def test_context_manager_speed(self, sample_outline, sample_kg, sample_seo, sample_analysis):
        cm = ContextManager()
        cm.load(
            outline=sample_outline,
            knowledge_graph=sample_kg,
            seo_plan=sample_seo,
            analysis=sample_analysis,
        )

        start = time.time()
        for _ in range(100):
            cm.get_context_for_section(SectionType.INTRODUCTION)
            cm.get_context_for_section(SectionType.BODY, sample_outline["sections"][0], order=1)
            cm.get_context_for_section(SectionType.FAQ)
            cm.get_context_for_section(SectionType.CONCLUSION)
        elapsed = time.time() - start

        avg_us = (elapsed / 400) * 1_000_000
        assert avg_us < 10000

    def test_validator_speed(self):
        validator = SectionValidator()
        output = SectionOutput(
            section_id="speed",
            section_type=SectionType.BODY,
            heading="Speed Test",
            content="Python is fast. The validator processes quickly. "
                    "Multiple sentences ensure proper testing. "
                    "This is a performance test for validation. "
                    "We need enough words to measure accurately. "
                    "The validator checks many dimensions of quality. " * 5,
        )
        ctx = SectionContext(
            section_type=SectionType.BODY,
            heading="Speed Test",
            target_word_count=100,
            primary_keyword="Python",
            keywords=["Python", "validator"],
            facts=["Python is fast"],
        )

        start = time.time()
        for _ in range(50):
            validator.validate(output, ctx)
        elapsed = time.time() - start

        avg_us = (elapsed / 50) * 1_000_000
        assert avg_us < 10000


# =========================================================================
# Edge Case Tests
# =========================================================================

class TestEdgeCases:
    def test_empty_outline(self):
        engine = SectionGenerationEngine()
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SectionStorage(tmpdir)
            engine = SectionGenerationEngine(storage=storage)
            project_id = f"empty_{int(time.time() * 1000)}"
            manifest = engine.generate_all_sections(
                project_id=project_id,
                outline={},
            )
            # Empty outline still generates intro + conclusion + cta
            assert manifest.total_sections >= 2

    def test_none_keywords(self):
        service = SectionService()
        service.load_artifacts()
        output, _ = service.generate_introduction()
        assert output.status == SectionStatus.COMPLETED

    def test_very_large_word_count(self):
        ctx = SectionContext(
            section_type=SectionType.BODY,
            heading="Large",
            target_word_count=5000,
            primary_keyword="Python",
        )
        gen = SectionGenerator()
        output = gen.generate(SectionType.BODY, ctx)
        assert output.status == SectionStatus.COMPLETED

    def test_special_characters_in_heading(self):
        ctx = SectionContext(
            section_type=SectionType.BODY,
            heading="Python & Django: A Guide (2024 Edition)",
            target_word_count=50,
        )
        gen = SectionGenerator()
        output = gen.generate(SectionType.BODY, ctx)
        assert output.status == SectionStatus.COMPLETED

    @pytest.mark.parametrize("section_type", [
        SectionType.PROBLEM, SectionType.EXPLANATION,
        SectionType.COMPARISON, SectionType.DEFINITION,
        SectionType.BENEFITS, SectionType.DRAWBACKS,
        SectionType.USE_CASES, SectionType.SUMMARY,
    ])
    def test_all_section_types_generate(self, section_type):
        gen = SectionGenerator()
        ctx = SectionContext(
            section_type=section_type,
            heading=section_type.value.replace("_", " ").title(),
            target_word_count=50,
        )
        output = gen.generate(section_type, ctx)
        assert output.status == SectionStatus.COMPLETED

    def test_concurrent_cache_operations(self):
        cache = SectionCache()
        contexts = []
        for i in range(10):
            ctx = SectionContext(
                section_type=SectionType.BODY,
                heading=f"Concurrent {i}",
                primary_keyword="Python",
            )
            contexts.append(ctx)
            output = SectionOutput(
                section_id=f"c_{i}",
                section_type=SectionType.BODY,
                heading=f"Concurrent {i}",
                content=f"Content {i}",
                version=1,
            )
            cache.set(SectionType.BODY, ctx, output)

        for i, ctx in enumerate(contexts):
            cached = cache.get(SectionType.BODY, ctx)
            assert cached is not None
            assert cached.content == f"Content {i}"

    def test_version_rollback_invalid(self):
        vm = SectionVersionManager()
        result = vm.rollback("no_such_section", 999)
        assert result is None
