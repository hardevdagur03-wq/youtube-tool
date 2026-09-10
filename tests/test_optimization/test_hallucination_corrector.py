"""Tests for HallucinationCorrector."""

from __future__ import annotations
from optimization.hallucination_corrector import HallucinationCorrector
from optimization.optimization_models import OptimizationContext


def fake_llm(system_prompt="", user_prompt="", temperature=0.3, max_tokens=2048):
    return "Python is a programming language created by Guido van Rossum. It is widely used."


class TestHallucinationCorrector:
    def test_init(self):
        hc = HallucinationCorrector()
        assert hc is not None

    def test_optimize_clean_content(self):
        hc = HallucinationCorrector()
        ctx = OptimizationContext(
            section_text="Python is a programming language.",
            knowledge_graph={"facts": [{"statement": "Python is a programming language"}]},
        )
        result, warnings = hc.optimize(ctx, fake_llm)
        assert len(result) > 0

    def test_detect_hallucination_patterns(self):
        hc = HallucinationCorrector()
        text = "According to a 2023 study by Harvard, Python is the best language. Studies show that 95% of developers prefer it."
        detected, warnings = hc._detect_hallucinations(text, {})
        assert len(detected) > 0
        assert len(warnings) > 0

    def test_detect_clean_content(self):
        hc = HallucinationCorrector()
        text = "Python is a programming language created by Guido van Rossum."
        detected, warnings = hc._detect_hallucinations(text, {})
        assert len(detected) == 0

    def test_extract_kg_facts(self):
        hc = HallucinationCorrector()
        kg = {
            "facts": [{"statement": "Python was created in 1991"}, {"statement": "Python is dynamically typed"}],
            "statistics": [{"value": "8.2 million developers", "context": "Python developer survey"}],
        }
        facts = hc._extract_kg_facts(kg)
        assert len(facts) == 3

    def test_extract_kg_facts_empty(self):
        hc = HallucinationCorrector()
        facts = hc._extract_kg_facts({})
        assert facts == []
