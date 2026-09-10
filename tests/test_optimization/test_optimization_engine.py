"""Tests for OptimizationEngine."""

from __future__ import annotations
from optimization.optimization_engine import OptimizationEngine
from optimization.optimization_models import OptimizationConfig, QualityGate


SAMPLE_DRAFT = """# Python Testing Guide

## Introduction

Testing is important for software quality.

## Methods

Unit tests verify individual components. Integration tests check how components work together.

## Conclusion

Testing is essential.
"""

SAMPLE_REVIEW = {
    "metadata": {"blog_title": "Python Testing Guide", "project_id": "test_123"},
    "quality_scores": {
        "seo": 75.0, "grammar": 88.0, "readability": 82.0,
        "hallucination_risk": 95.0, "structure": 90.0,
    },
    "issues": [{"description": "Low keyword density", "location": "Introduction", "severity": "medium"}],
    "recommendations": [{"description": "Add primary keyword to introduction", "priority": "must_fix", "category": "seo"}],
}

SAMPLE_OUTLINE = {"sections": [{"heading": "# Python Testing Guide", "description": "Overview of testing"}]}
SAMPLE_SEO = {"keyword_strategy": {"primary": "testing", "secondary": ["unit", "integration"]}}
SAMPLE_KG = {"facts": [{"statement": "Testing ensures code quality"}], "statistics": []}
SAMPLE_PROJECT = {"project_id": "test_123", "title": "Python Testing Guide"}


def fake_llm(system_prompt="", user_prompt="", temperature=0.3, max_tokens=2048):
    return "Testing is very important for software quality. Unit tests and integration tests help ensure code reliability."


class TestOptimizationEngine:
    def test_init(self):
        e = OptimizationEngine()
        assert e is not None

    def test_optimize_no_llm(self):
        e = OptimizationEngine()
        draft, report = e.optimize(
            draft_md=SAMPLE_DRAFT,
            review_report=SAMPLE_REVIEW,
            outline=SAMPLE_OUTLINE,
            seo_plan=SAMPLE_SEO,
            knowledge_graph=SAMPLE_KG,
            project=SAMPLE_PROJECT,
        )
        assert isinstance(draft, str)
        assert draft == SAMPLE_DRAFT  # No LLM = no changes
        assert report.total_sections == 4

    def test_optimize_with_llm(self):
        config = OptimizationConfig(max_retries=1)
        e = OptimizationEngine(config=config)
        draft, report = e.optimize(
            draft_md=SAMPLE_DRAFT,
            review_report=SAMPLE_REVIEW,
            outline=SAMPLE_OUTLINE,
            seo_plan=SAMPLE_SEO,
            knowledge_graph=SAMPLE_KG,
            project=SAMPLE_PROJECT,
            llm_call=fake_llm,
        )
        assert isinstance(draft, str)
        assert report.total_sections == 4

    def test_parse_sections(self):
        e = OptimizationEngine()
        sections = e._parse_sections(SAMPLE_DRAFT)
        assert len(sections) == 4  # Title + Intro + Methods + Conclusion

    def test_extract_primary_keyword(self):
        e = OptimizationEngine()
        kw = e._extract_primary_keyword(SAMPLE_SEO, SAMPLE_REVIEW)
        assert kw == "testing"

    def test_extract_primary_keyword_empty(self):
        e = OptimizationEngine()
        kw = e._extract_primary_keyword({}, {})
        assert kw == ""

    def test_quality_gates_pass(self):
        config = OptimizationConfig(quality_gates=QualityGate(seo_min=70.0, grammar_min=80.0, readability_min=75.0))
        e = OptimizationEngine(config=config)
        passed = e._check_quality_gates({"seo": 85.0, "grammar": 90.0, "readability": 88.0})
        assert passed is True

    def test_quality_gates_fail(self):
        config = OptimizationConfig(quality_gates=QualityGate(seo_min=90.0, grammar_min=95.0, readability_min=90.0))
        e = OptimizationEngine(config=config)
        passed = e._check_quality_gates({"seo": 85.0, "grammar": 90.0, "readability": 88.0})
        assert passed is False

    def test_write_outputs(self):
        import tempfile
        import os
        e = OptimizationEngine()
        draft, report = e.optimize(
            draft_md=SAMPLE_DRAFT,
            review_report=SAMPLE_REVIEW,
            outline=SAMPLE_OUTLINE,
            seo_plan=SAMPLE_SEO,
            knowledge_graph=SAMPLE_KG,
            project=SAMPLE_PROJECT,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = e.write_outputs(draft, report, output_dir=tmpdir, project_id="test_123")
            assert os.path.exists(paths["optimized_draft"])
            assert os.path.exists(paths["optimization_report"])
