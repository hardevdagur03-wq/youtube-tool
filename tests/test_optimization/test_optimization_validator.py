"""Tests for OptimizationValidator."""

from __future__ import annotations
from optimization.optimization_validator import OptimizationValidator
from optimization.optimization_models import OptimizationContext, OptimizationType, SectionType


class TestOptimizationValidator:
    def test_init(self):
        v = OptimizationValidator()
        assert v is not None

    def test_validate_identical(self):
        v = OptimizationValidator()
        ctx = OptimizationContext(section_text="Hello world")
        valid, warnings = v.validate("Hello world", "Hello world", ctx, [OptimizationType.SEO])
        assert valid is True

    def test_validate_empty_optimized(self):
        v = OptimizationValidator()
        ctx = OptimizationContext(section_text="Original")
        valid, warnings = v.validate("Original", "", ctx, [OptimizationType.GRAMMAR])
        assert valid is False

    def test_validate_content_loss(self):
        v = OptimizationValidator()
        ctx = OptimizationContext(section_text="This is a long original content that should be preserved.")
        valid, warnings = v.validate(
            "This is a long original content that should be preserved.",
            "Short",
            ctx,
            [OptimizationType.READABILITY],
        )
        assert valid is False

    def test_validate_code_block_preservation(self):
        v = OptimizationValidator()
        orig = "Some text\n```python\nprint('hello')\n```\nMore text"
        opt = "Some text\n```python\nprint('hello')\n```\nMore text"
        ctx = OptimizationContext(section_text=orig)
        valid, warnings = v.validate(orig, opt, ctx, [OptimizationType.STYLE])
        assert valid is True

    def test_validate_code_block_removed(self):
        v = OptimizationValidator()
        orig = "```python\nprint('hello')\n```"
        opt = "Some text without code"
        ctx = OptimizationContext(section_text=orig)
        valid, warnings = v.validate(orig, opt, ctx, [OptimizationType.STYLE])
        code_warnings = [w for w in warnings if "Code block" in w]
        assert len(code_warnings) > 0

    def test_validate_seo_keyword_missing(self):
        v = OptimizationValidator()
        ctx = OptimizationContext(
            section_text="Python is great.",
            primary_keyword="python",
        )
        valid, warnings = v.validate(
            "Python is great.",
            "It is a great language.",
            ctx,
            [OptimizationType.SEO],
        )
        keyword_warnings = [w for w in warnings if "keyword" in w.lower()]
        assert len(keyword_warnings) > 0

    def test_validate_hallucination_check(self):
        v = OptimizationValidator()
        ctx = OptimizationContext(section_text="Some content.")
        valid, warnings = v.validate(
            "Some content.",
            "According to a 2024 study by MIT, this is true.",
            ctx,
            [OptimizationType.HALLUCINATION],
        )
        assert len(warnings) > 0
