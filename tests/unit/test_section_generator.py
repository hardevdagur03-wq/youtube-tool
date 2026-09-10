from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest


class TestSectionModels:
    def test_section_type_enum(self):
        from section_generation.section_models import SectionType, SectionStatus
        assert SectionType.INTRODUCTION.value == "introduction"
        assert SectionStatus.COMPLETED.value == "completed"

    def test_section_context_creation(self):
        from section_generation.section_models import SectionContext, SectionType
        ctx = SectionContext(section_id="test_01", section_type=SectionType.BODY, heading="Test", goal="Test goal", order=1, target_word_count=300, keywords=["python"])
        assert ctx.section_id == "test_01"
        assert ctx.target_word_count == 300

    def test_section_output_creation(self):
        from section_generation.section_models import SectionOutput, SectionType, SectionStatus
        output = SectionOutput(section_id="intro", section_type=SectionType.INTRODUCTION, heading="Introduction", content="Test content.", order=0, word_count=2, status=SectionStatus.COMPLETED)
        assert output.word_count == 2

    def test_generation_result(self):
        from section_generation.section_models import GenerationResult
        result = GenerationResult(success=True, content="Generated content", tokens_input=100, tokens_output=50, latency_ms=500.0)
        assert result.success

    def test_generate_section_id(self):
        from section_generation.section_models import generate_section_id, SectionType
        assert generate_section_id(SectionType.INTRODUCTION) == "intro"
        assert generate_section_id(SectionType.BODY, 1) == "section_01"

    def test_estimate_reading_time(self):
        from section_generation.section_models import estimate_reading_time_seconds
        assert estimate_reading_time_seconds(600) == 180


class TestContextManager:
    def test_load_and_get_context(self):
        from section_generation.context_manager import ContextManager
        from section_generation.section_models import SectionType
        cm = ContextManager()
        cm.load(outline={"sections": [{"heading": "Test", "goal": "G", "target_word_count": 200}]})
        ctx = cm.get_context_for_section(SectionType.INTRODUCTION)
        assert ctx.section_type == SectionType.INTRODUCTION

    def test_get_faq_plan(self):
        from section_generation.context_manager import ContextManager
        cm = ContextManager()
        cm.load(outline={"faqs": [{"question": "Q?", "answer_summary": "A"}]})
        faqs = cm.get_faq_plan()
        assert len(faqs) == 1

    def test_get_cta_plan(self):
        from section_generation.context_manager import ContextManager
        cm = ContextManager()
        cm.load(outline={"ctas": [{"type": "primary", "text": "Subscribe"}]})
        ctas = cm.get_cta_plan()
        assert len(ctas) == 1

    def test_get_section_plan(self):
        from section_generation.context_manager import ContextManager
        cm = ContextManager()
        plan = {"heading": "Intro", "goal": "Hook", "target_word_count": 200}
        cm.load(outline={"intro_plan": plan, "sections": []})
        section = cm.get_outline_section(0)
        assert section is not None


class TestPromptBuilder:
    def test_build_intro_prompt(self):
        from section_generation.prompt_builder import PromptBuilder
        from section_generation.section_models import SectionContext, SectionType
        builder = PromptBuilder()
        ctx = SectionContext(section_type=SectionType.INTRODUCTION, heading="Introduction", goal="Hook", target_word_count=200, primary_keyword="Python")
        prompt = builder.build(ctx, SectionType.INTRODUCTION)
        assert "Python" in prompt.user_prompt
        assert prompt.system_prompt

    def test_build_body_prompt(self):
        from section_generation.prompt_builder import PromptBuilder
        from section_generation.section_models import SectionContext, SectionType
        builder = PromptBuilder()
        ctx = SectionContext(section_type=SectionType.BODY, heading="Features", goal="Explain", target_word_count=300, primary_keyword="Python")
        prompt = builder.build(ctx, SectionType.BODY)
        assert "Features" in prompt.user_prompt


class TestSectionCache:
    def test_cache_hit_and_miss(self):
        from section_generation.section_cache import SectionCache
        from section_generation.section_models import SectionContext, SectionType, SectionOutput
        cache = SectionCache()
        ctx = SectionContext(section_type=SectionType.BODY, heading="Test", primary_keyword="Python")
        result = cache.get(SectionType.BODY, ctx)
        assert result is None
        output = SectionOutput(section_id="test", section_type=SectionType.BODY, heading="Test", content="Test content", version=1)
        cache.set(SectionType.BODY, ctx, output)
        cached = cache.get(SectionType.BODY, ctx)
        assert cached is not None
        assert cached.cache_hit

    def test_cache_invalidation(self):
        from section_generation.section_cache import SectionCache
        from section_generation.section_models import SectionContext, SectionType, SectionOutput
        cache = SectionCache()
        ctx = SectionContext(section_type=SectionType.BODY, heading="Test", primary_keyword="Python")
        output = SectionOutput(section_id="test", section_type=SectionType.BODY, content="Test", version=1)
        cache.set(SectionType.BODY, ctx, output)
        cache.invalidate(SectionType.BODY, ctx)
        result = cache.get(SectionType.BODY, ctx)
        assert result is None

    def test_cache_clear(self):
        from section_generation.section_cache import SectionCache
        from section_generation.section_models import SectionContext, SectionType, SectionOutput
        cache = SectionCache()
        ctx = SectionContext(section_type=SectionType.BODY, heading="Test", primary_keyword="Python")
        output = SectionOutput(section_id="test", section_type=SectionType.BODY, content="Test", version=1)
        cache.set(SectionType.BODY, ctx, output)
        cache.clear()
        assert cache._store == {}


class TestSectionValidator:
    def test_valid_section(self):
        from section_generation.section_validator import SectionValidator
        from section_generation.section_models import SectionOutput, SectionContext, SectionType
        validator = SectionValidator()
        output = SectionOutput(section_id="test_01", section_type=SectionType.BODY, heading="Python Features", content="Python is a versatile programming language used by millions. It supports multiple paradigms. The syntax is simple and clean.", order=1)
        ctx = SectionContext(section_type=SectionType.BODY, heading="Python Features", target_word_count=50, primary_keyword="Python")
        validation = validator.validate(output, ctx)
        assert validation.score >= 60 or validation.valid

    def test_empty_section(self):
        from section_generation.section_validator import SectionValidator
        from section_generation.section_models import SectionOutput, SectionType
        validator = SectionValidator()
        output = SectionOutput(section_id="empty", section_type=SectionType.BODY, heading="Empty", content="")
        validation = validator.validate(output)
        assert not validation.valid

    def test_duplicate_sentences(self):
        from section_generation.section_validator import SectionValidator
        from section_generation.section_models import SectionOutput, SectionType
        validator = SectionValidator()
        output = SectionOutput(section_id="dup", section_type=SectionType.BODY, heading="Duplicates", content="Python is a versatile language used widely. Python is a versatile language used widely.")
        validation = validator.validate(output)
        assert validation.duplicate_content_score < 1.0


class TestSectionVersionManager:
    def test_create_and_get_version(self):
        from section_generation.section_version_manager import SectionVersionManager
        from section_generation.section_models import SectionOutput, SectionType
        vm = SectionVersionManager()
        output = SectionOutput(section_id="test_01", section_type=SectionType.BODY, heading="Test", content="Version 1 content", version=1)
        sv = vm.create_version("test_01", output, reason="initial")
        assert sv.version_number == 1
        retrieved = vm.get_version("test_01", 1)
        assert retrieved is not None

    def test_multiple_versions(self):
        from section_generation.section_version_manager import SectionVersionManager
        from section_generation.section_models import SectionOutput, SectionType
        vm = SectionVersionManager()
        for i in range(3):
            output = SectionOutput(section_id="multi", section_type=SectionType.BODY, heading="Multi", content=f"Version {i+1}", version=i+1)
            vm.create_version("multi", output, reason=f"v{i+1}")
        history = vm.get_version_history("multi")
        assert len(history) == 3

    def test_rollback(self):
        from section_generation.section_version_manager import SectionVersionManager
        from section_generation.section_models import SectionOutput, SectionType
        vm = SectionVersionManager()
        output = SectionOutput(section_id="rb", section_type=SectionType.BODY, heading="RB", content="Original", version=1)
        vm.create_version("rb", output, reason="original")
        output.content = "Updated"
        vm.create_version("rb", output, reason="update")
        rolled = vm.rollback("rb", 1)
        assert rolled == "Original"


class TestSectionGenerator:
    def test_generate_without_provider(self):
        from section_generation.section_generator import SectionGenerator
        from section_generation.section_models import SectionContext, SectionType, SectionStatus
        gen = SectionGenerator()
        ctx = SectionContext(section_type=SectionType.INTRODUCTION, heading="Intro", goal="Test", target_word_count=50)
        output = gen.generate(SectionType.INTRODUCTION, ctx)
        assert output.status == SectionStatus.COMPLETED
        assert output.content

    def test_generate_body_section(self):
        from section_generation.section_generator import SectionGenerator
        from section_generation.section_models import SectionContext, SectionType, SectionStatus
        gen = SectionGenerator()
        ctx = SectionContext(section_type=SectionType.BODY, heading="Features", goal="Explain", target_word_count=100, primary_keyword="Python")
        output = gen.generate(SectionType.BODY, ctx)
        assert output.status == SectionStatus.COMPLETED
        assert output.heading == "Features"

    def test_generate_faq(self):
        from section_generation.section_generator import SectionGenerator
        from section_generation.section_models import SectionContext, SectionType, SectionStatus
        gen = SectionGenerator()
        ctx = SectionContext(section_type=SectionType.FAQ, primary_keyword="Python")
        output = gen.generate(SectionType.FAQ, ctx)
        assert output.status == SectionStatus.COMPLETED


class TestSectionService:
    def test_generate_introduction(self):
        from section_generation.section_service import SectionService
        svc = SectionService()
        svc.load_artifacts(outline={"sections": [{"heading": "Test", "target_word_count": 200}]})
        output, validation = svc.generate_introduction()
        assert output.status.value == "completed"

    def test_generate_faq_service(self):
        from section_generation.section_service import SectionService
        svc = SectionService()
        svc.load_artifacts(outline={"faqs": [{"question": "Q?"}]})
        output, validation = svc.generate_faq()
        assert output.status.value == "completed"


class TestSectionGenerationEngine:
    def test_engine_initialization(self):
        from section_generation.section_engine import SectionGenerationEngine
        engine = SectionGenerationEngine()
        assert engine.get_progress() is None
        assert engine.get_manifest() is None

    def test_engine_progress_tracking(self):
        from section_generation.section_engine import SectionGenerationEngine
        from section_generation.section_storage import SectionStorage
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SectionStorage(tmpdir)
            engine = SectionGenerationEngine(storage=storage)
            project_id = f"progress_{int(time.time())}"
            progress_reports = []
            def on_progress(report):
                progress_reports.append(report)
            engine.set_on_progress(on_progress)
            manifest = engine.generate_all_sections(project_id=project_id, outline={})
            assert len(progress_reports) > 0

    def test_engine_single_section(self):
        from section_generation.section_engine import SectionGenerationEngine
        from section_generation.section_storage import SectionStorage
        from section_generation.section_models import SectionType
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SectionStorage(tmpdir)
            engine = SectionGenerationEngine(storage=storage)
            engine.load_artifacts(outline={"sections": []})
            project_id = f"single_{int(time.time())}"
            output, validation = engine.generate_single_section(project_id, SectionType.INTRODUCTION, {}, order=0)
            assert output.status.value in ("completed", "failed")
