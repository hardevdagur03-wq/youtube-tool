"""Tests for GrammarOptimizer."""

from __future__ import annotations
from optimization.grammar_optimizer import GrammarOptimizer
from optimization.optimization_models import OptimizationContext, SectionType


def fake_llm(system_prompt="", user_prompt="", temperature=0.3, max_tokens=2048):
    return "This is a grammatically correct sentence. It has no errors."


def failing_llm(system_prompt="", user_prompt="", temperature=0.3, max_tokens=2048):
    raise Exception("LLM failed")


class TestGrammarOptimizer:
    def test_init(self):
        opt = GrammarOptimizer()
        assert opt is not None

    def test_optimize_with_llm(self):
        opt = GrammarOptimizer()
        ctx = OptimizationContext(
            section_text="This has definately a spelling error. And recieve is wrong.",
        )
        result, warnings = opt.optimize(ctx, fake_llm)
        assert len(result) > 0

    def test_optimize_llm_failure_uses_quick_fixes(self):
        opt = GrammarOptimizer()
        ctx = OptimizationContext(
            section_text="this sentence has a capitalization error. recieve is misspelled.",
        )
        result, warnings = opt.optimize(ctx, failing_llm)
        # Quick fixes should have been applied
        assert "recieve" not in result
        assert len(warnings) > 0

    def test_quick_grammar_fixes_spelling(self):
        opt = GrammarOptimizer()
        fixed, warnings = opt._quick_grammar_fixes("This is definately wrong. Recieve this.")
        assert "definitely" in fixed
        assert "Receive" in fixed or "receive" in fixed
        assert len(warnings) > 0

    def test_quick_grammar_fixes_capitalization(self):
        opt = GrammarOptimizer()
        fixed, warnings = opt._quick_grammar_fixes("first sentence starts lowercase. second is fine.")
        assert fixed[0].isupper()

    def test_empty_content(self):
        opt = GrammarOptimizer()
        ctx = OptimizationContext(section_text="")
        result, warnings = opt.optimize(ctx, fake_llm)
        assert isinstance(result, str)
