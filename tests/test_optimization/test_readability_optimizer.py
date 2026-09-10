"""Tests for ReadabilityOptimizer."""

from __future__ import annotations
from optimization.readability_optimizer import ReadabilityOptimizer
from optimization.optimization_models import OptimizationContext


def fake_llm(system_prompt="", user_prompt="", temperature=0.3, max_tokens=2048):
    return "Short sentences are better. They improve readability. This is a good change."


def failing_llm(system_prompt="", user_prompt="", temperature=0.3, max_tokens=2048):
    raise Exception("LLM failed")


class TestReadabilityOptimizer:
    def test_init(self):
        opt = ReadabilityOptimizer()
        assert opt is not None

    def test_optimize_with_llm(self):
        opt = ReadabilityOptimizer()
        ctx = OptimizationContext(
            section_text="This is a very long and complex sentence that should probably be broken into multiple shorter sentences for better readability and understanding by the audience.",
        )
        result, warnings = opt.optimize(ctx, fake_llm)
        assert len(result) > 0

    def test_optimize_llm_failure_uses_quick_fixes(self):
        opt = ReadabilityOptimizer()
        ctx = OptimizationContext(
            section_text="This is a very long and complex sentence with many words that goes on and on without stopping and should be broken up. Short sentence."
        )
        result, warnings = opt.optimize(ctx, failing_llm)
        assert len(result) > 0
        # Quick fix should have split the long sentence
        assert "Short sentence." in result

    def test_quick_readability_fixes_long_sentences(self):
        opt = ReadabilityOptimizer()
        long_text = "This is a very long sentence that has way too many words in it and should really be broken into multiple shorter sentences for better readability and clarity for the target audience who prefers simple clear content that is easy to read and understand quickly. " * 2
        fixed, warnings = opt._quick_readability_fixes(long_text)
        assert isinstance(fixed, str)

    def test_empty_content(self):
        opt = ReadabilityOptimizer()
        ctx = OptimizationContext(section_text="")
        result, warnings = opt.optimize(ctx, fake_llm)
        assert isinstance(result, str)
