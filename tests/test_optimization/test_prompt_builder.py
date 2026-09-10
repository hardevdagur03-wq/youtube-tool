"""Tests for PromptBuilder."""

from __future__ import annotations
from optimization.prompt_builder import PromptBuilder, SYSTEM_PROMPTS
from optimization.optimization_models import OptimizationType, OptimizationContext, SectionType


class TestPromptBuilder:
    def test_init(self):
        pb = PromptBuilder()
        assert pb is not None

    def test_system_prompts_defined(self):
        for opt_type in OptimizationType:
            assert opt_type in SYSTEM_PROMPTS, f"Missing system prompt for {opt_type.value}"

    def test_build_seo_prompt(self):
        pb = PromptBuilder()
        ctx = OptimizationContext(
            section_text="# Introduction\nPython is great.",
            section_heading="# Introduction",
            primary_keyword="python",
            secondary_keywords=["code", "testing"],
        )
        prompt = pb.build_prompt(ctx, OptimizationType.SEO)
        assert "python" in prompt.system_prompt
        assert "Primary Keyword" in prompt.system_prompt
        assert "CRITICAL RULES" in prompt.system_prompt
        assert prompt.optimization_type == OptimizationType.SEO

    def test_build_grammar_prompt(self):
        pb = PromptBuilder()
        ctx = OptimizationContext(
            section_text="This is a test.",
            issues=[{"description": "Spelling error: definately"}],
        )
        prompt = pb.build_prompt(ctx, OptimizationType.GRAMMAR)
        assert "define" in prompt.user_prompt or "spelling" in prompt.user_prompt.lower()

    def test_build_hallucination_prompt(self):
        pb = PromptBuilder()
        ctx = OptimizationContext(
            section_text="Studies show this is true.",
            knowledge_graph={"facts": [{"statement": "Python is a programming language"}]},
        )
        prompt = pb.build_prompt(ctx, OptimizationType.HALLUCINATION)
        assert "Verified facts" in prompt.user_prompt or "Hallucination" in prompt.system_prompt

    def test_build_readability_prompt(self):
        pb = PromptBuilder()
        ctx = OptimizationContext(section_text="This is a very long and complex sentence that should probably be split into multiple shorter sentences for better readability.")
        prompt = pb.build_prompt(ctx, OptimizationType.READABILITY)
        assert prompt.optimization_type == OptimizationType.READABILITY

    def test_default_goals(self):
        pb = PromptBuilder()
        seo_goals = pb._default_goals(OptimizationType.SEO)
        assert len(seo_goals) > 0
        assert "Improve keyword placement" in seo_goals

    def test_target_scores(self):
        pb = PromptBuilder()
        scores = pb._target_scores(OptimizationType.SEO)
        assert scores.get("seo") == 90.0

        scores = pb._target_scores(OptimizationType.GRAMMAR)
        assert scores.get("grammar") == 95.0

    def test_build_user_prompt_with_goals(self):
        pb = PromptBuilder()
        ctx = OptimizationContext(section_text="Test content.")
        prompt = pb.build_prompt(ctx, OptimizationType.SEO, ["Improve keyword density"])
        assert "Improve keyword density" in prompt.user_prompt
