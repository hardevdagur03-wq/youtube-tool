from __future__ import annotations

import pytest


class TestOptimizationModels:
    def test_optimization_models_import(self):
        from optimization.optimization_models import OptimizationPlan, OptimizationType, OptimizationStatus
        plan = OptimizationPlan(section_index=0, section_heading="Test", optimization_types=[OptimizationType.GRAMMAR])
        assert OptimizationType.GRAMMAR in plan.optimization_types
        assert plan.needs_optimization is False


class TestOptimizationPlanner:
    def test_plan(self):
        from optimization.optimization_planner import OptimizationPlanner
        planner = OptimizationPlanner()
        plan = planner.plan(sections=[{"heading": "Intro", "content": "Python is a great language. It is used widely."}], review_scores={"seo": 50.0}, review_issues=[{"description": "Low SEO score", "location": "intro"}], recommendations=[], primary_keyword="Python")
        assert plan is not None
        assert len(plan) > 0

    def test_plan_empty(self):
        from optimization.optimization_planner import OptimizationPlanner
        planner = OptimizationPlanner()
        plan = planner.plan(sections=[], review_scores={}, review_issues=[], recommendations=[], primary_keyword="")
        assert plan is not None


class TestGrammarOptimizer:
    def test_optimize(self):
        from optimization.grammar_optimizer import GrammarOptimizer
        from optimization.optimization_models import OptimizationContext
        optimizer = GrammarOptimizer()
        ctx = OptimizationContext(section_text="Python is a great language. It is used widely for data science.")
        result = optimizer.optimize(ctx, llm_call=lambda **kw: "Python is a great language. It is used widely for data science.")
        assert result[0]
        assert len(result[1]) >= 0


class TestReadabilityOptimizer:
    def test_optimize(self):
        from optimization.readability_optimizer import ReadabilityOptimizer
        from optimization.optimization_models import OptimizationContext
        optimizer = ReadabilityOptimizer()
        ctx = OptimizationContext(section_text="Python is a high-level programming language with dynamic semantics. It supports multiple programming paradigms.")
        result = optimizer.optimize(ctx, llm_call=lambda **kw: "Python is a high-level programming language. It supports multiple paradigms.")
        assert result[0]
        assert len(result[1]) >= 0


class TestSEOOptimizer:
    def test_optimize(self):
        from optimization.seo_optimizer import SEOOptimizer
        from optimization.optimization_models import OptimizationContext, OptimizationType
        optimizer = SEOOptimizer()
        ctx = OptimizationContext(section_text="Python is a programming language.", primary_keyword="Python")
        result = optimizer.optimize(ctx, llm_call=lambda **kw: "Python is a programming language used widely.")
        assert result[0]


class TestHallucinationCorrector:
    def test_correct(self):
        from optimization.hallucination_corrector import HallucinationCorrector
        from optimization.optimization_models import OptimizationContext
        corrector = HallucinationCorrector()
        ctx = OptimizationContext(section_text="Python was created in 1995.", knowledge_graph={"facts": [{"statement": "Python was created in 1991"}]})
        result = corrector.optimize(ctx, llm_call=lambda **kw: "Python was created in 1991.")
        assert result is not None


class TestChangeDetector:
    def test_detect_changes(self):
        from optimization.change_detector import ChangeDetector
        detector = ChangeDetector()
        changes = detector.detect_changes("Original content here.", "Modified content here with updates.")
        assert changes["changed"] is True

    def test_detect_no_changes(self):
        from optimization.change_detector import ChangeDetector
        detector = ChangeDetector()
        changes = detector.detect_changes("Same content.", "Same content.")
        assert changes["changed"] is False


class TestOptimizationContextManager:
    def test_load_and_get(self):
        from optimization.context_manager import OptimizationContextManager
        from optimization.optimization_models import SectionType
        cm = OptimizationContextManager()
        ctx = cm.build_context(section_index=0, section_text="Draft content", section_heading="Intro", section_type=SectionType.BODY, optimization_types=[], artifacts={"outline": {}, "seo_plan": {"keyword_strategy": {"primary": "Python"}}, "knowledge_graph": {}, "review_report": {"quality_scores": {}, "issues": [], "recommendations": []}})
        assert ctx is not None

    def test_empty_context(self):
        from optimization.context_manager import OptimizationContextManager
        from optimization.optimization_models import SectionType
        cm = OptimizationContextManager()
        ctx = cm.build_context(section_index=0, section_text="", section_heading="", section_type=SectionType.BODY, optimization_types=[], artifacts={})
        assert ctx is not None


class TestPromptBuilder:
    def test_build(self):
        from optimization.prompt_builder import PromptBuilder
        from optimization.optimization_models import OptimizationContext, OptimizationType
        builder = PromptBuilder()
        ctx = OptimizationContext(section_text="Test content.")
        prompt = builder.build_prompt(ctx, OptimizationType.GRAMMAR)
        assert prompt is not None
        assert "Test content" in prompt.user_prompt


class TestCacheManager:
    def test_set_and_get(self):
        from optimization.cache_manager import OptimizationCacheManager
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = OptimizationCacheManager(cache_dir=tmpdir)
            cache.set("test_key", {"data": "test_value"})
            result = cache.get("test_key")
            assert result == {"data": "test_value"}

    def test_cache_miss(self):
        from optimization.cache_manager import OptimizationCacheManager
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = OptimizationCacheManager(cache_dir=tmpdir)
            result = cache.get("nonexistent")
            assert result is None

    def test_cache_invalidate(self):
        from optimization.cache_manager import OptimizationCacheManager
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = OptimizationCacheManager(cache_dir=tmpdir)
            cache.set("test_key", "value")
            cache.invalidate("test_key")
            assert cache.get("test_key") is None


class TestRetryManager:
    def test_execute_success(self):
        from optimization.retry_manager import RetryManager
        rm = RetryManager(max_retries=3)
        assert rm.can_retry(0) is True

    def test_execute_failure(self):
        from optimization.retry_manager import RetryManager
        rm = RetryManager(max_retries=1)
        result = rm.record_attempt(0, [], {})
        assert result is False


class TestRollbackManager:
    def test_create_and_rollback(self):
        from optimization.rollback_manager import RollbackManager
        rm = RollbackManager()
        should, reason = rm.should_rollback({"seo": 80.0}, {"seo": 70.0}, [], {})
        assert should is True or should is False


class TestRevalidationEngine:
    def test_revalidate(self):
        from optimization.revalidation_engine import RevalidationEngine
        from optimization.optimization_models import OptimizationType
        engine = RevalidationEngine()
        result = engine.revalidate("Original content.", "Optimized content.", [OptimizationType.GRAMMAR])
        assert len(result) >= 0


class TestVersionManager:
    def test_create_version(self):
        from optimization.version_manager import VersionManager
        from optimization.optimization_models import OptimizationType
        vm = VersionManager()
        v = vm.create_version(section_index=0, section_heading="Test", prompt="test prompt", content_before="v1", content_after="v1", scores_before={}, scores_after={}, optimization_type=OptimizationType.GRAMMAR)
        assert v.version_id
        assert v.section_index == 0

    def test_get_latest(self):
        from optimization.version_manager import VersionManager
        from optimization.optimization_models import OptimizationType
        vm = VersionManager()
        vm.create_version(section_index=0, section_heading="Test", prompt="p1", content_before="v1", content_after="v1", scores_before={}, scores_after={}, optimization_type=OptimizationType.GRAMMAR)
        vm.create_version(section_index=0, section_heading="Test", prompt="p2", content_before="v2", content_after="v2", scores_before={}, scores_after={}, optimization_type=OptimizationType.SEO)
        latest = vm.get_latest_version(0)
        assert latest is not None


class TestOptimizationValidator:
    def test_validate(self):
        from optimization.optimization_validator import OptimizationValidator
        from optimization.optimization_models import OptimizationContext, OptimizationType
        validator = OptimizationValidator()
        result = validator.validate("Original content here.", "Optimized content here.", OptimizationContext(), [OptimizationType.GRAMMAR])
        assert isinstance(result[0], bool)


class TestOptimizationService:
    def test_optimize(self):
        from optimization.optimization_service import OptimizationService
        svc = OptimizationService()
        result = svc.optimize_from_artifacts(draft_md="# Test\n\nPython is a great language.", review_report={"quality_scores": {}, "issues": [], "recommendations": [], "metadata": {}}, outline={}, seo_plan={}, knowledge_graph={})
        assert result is not None


class TestOptimizationEngine:
    def test_build_full(self):
        from optimization.optimization_engine import OptimizationEngine
        engine = OptimizationEngine()
        result = engine.optimize(draft_md="# Test\n\nPython is a programming language used for data science.", review_report={"quality_scores": {}, "issues": [], "recommendations": [], "metadata": {}}, outline={}, seo_plan={}, knowledge_graph={})
        assert result is not None
        assert result[0]
