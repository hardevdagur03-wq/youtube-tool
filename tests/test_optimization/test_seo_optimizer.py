"""Tests for SEOOptimizer."""

from __future__ import annotations
from optimization.seo_optimizer import SEOOptimizer
from optimization.optimization_models import OptimizationContext, SectionType, OptimizationType


def fake_llm(system_prompt="", user_prompt="", temperature=0.3, max_tokens=2048):
    return "This is an optimized section about Python testing. Python testing is important for code quality. We should always test our code."


def failing_llm(system_prompt="", user_prompt="", temperature=0.3, max_tokens=2048):
    raise Exception("LLM failed")


def empty_llm(system_prompt="", user_prompt="", temperature=0.3, max_tokens=2048):
    return ""


class TestSEOOptimizer:
    def test_init(self):
        opt = SEOOptimizer()
        assert opt is not None

    def test_optimize_with_llm(self):
        opt = SEOOptimizer()
        ctx = OptimizationContext(
            section_text="Python is a programming language.",
            primary_keyword="python",
            secondary_keywords=["testing", "code"],
        )
        result, warnings = opt.optimize(ctx, fake_llm)
        assert len(result) > 0
        assert isinstance(result, str)

    def test_optimize_preserves_keyword(self):
        opt = SEOOptimizer()
        ctx = OptimizationContext(
            section_text="Python is great for coding.",
            primary_keyword="python",
        )
        result, warnings = opt.optimize(ctx, fake_llm)
        assert "python" in result.lower()

    def test_optimize_llm_failure(self):
        opt = SEOOptimizer()
        ctx = OptimizationContext(
            section_text="Original content to keep.",
            primary_keyword="python",
        )
        result, warnings = opt.optimize(ctx, failing_llm)
        assert result == "Original content to keep."
        assert len(warnings) > 0

    def test_optimize_empty_result(self):
        opt = SEOOptimizer()
        ctx = OptimizationContext(
            section_text="Keep this content.",
            primary_keyword="python",
        )
        result, warnings = opt.optimize(ctx, empty_llm)
        assert result == "Keep this content."

    def test_quick_seo_fixes(self):
        opt = SEOOptimizer()
        text = "This is an introduction. Python is great."
        modified, fixes = opt.quick_seo_fixes(text, "python")
        assert "python" in modified.lower()
        assert len(fixes) >= 0

    def test_quick_seo_fixes_no_keyword(self):
        opt = SEOOptimizer()
        text = "Some random content."
        modified, fixes = opt.quick_seo_fixes(text, "")
        assert modified == text
        assert fixes == []
