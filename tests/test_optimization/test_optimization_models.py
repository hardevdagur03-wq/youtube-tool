"""Tests for optimization models."""

from __future__ import annotations
from optimization.optimization_models import (
    OptimizationType, OptimizationStatus, SectionType, QualityGate,
    OptimizationContext, OptimizationPrompt, SectionVersion,
    OptimizationResult, OptimizationPlan, OptimizationReport,
    OptimizationConfig, OptimizedSection, OptimizedDraft,
)


class TestEnums:
    def test_optimization_type_values(self):
        assert OptimizationType.SEO.value == "seo"
        assert OptimizationType.GRAMMAR.value == "grammar"
        assert OptimizationType.READABILITY.value == "readability"
        assert OptimizationType.HALLUCINATION.value == "hallucination"

    def test_optimization_status_values(self):
        assert OptimizationStatus.PENDING.value == "pending"
        assert OptimizationStatus.SUCCESS.value == "success"
        assert OptimizationStatus.ROLLED_BACK.value == "rolled_back"

    def test_section_type_values(self):
        assert SectionType.INTRODUCTION.value == "introduction"
        assert SectionType.BODY.value == "body"
        assert SectionType.FAQ.value == "faq"


class TestQualityGate:
    def test_defaults(self):
        g = QualityGate()
        assert g.seo_min == 90.0
        assert g.grammar_min == 95.0
        assert g.readability_min == 90.0
        assert g.hallucination_max_risk == "low"

    def test_custom(self):
        g = QualityGate(seo_min=85.0, grammar_min=90.0)
        assert g.seo_min == 85.0
        assert g.grammar_min == 90.0


class TestOptimizationContext:
    def test_defaults(self):
        ctx = OptimizationContext()
        assert ctx.section_text == ""
        assert ctx.primary_keyword == ""
        assert ctx.section_type == SectionType.BODY

    def test_with_data(self):
        ctx = OptimizationContext(
            section_text="# Hello\nWorld",
            primary_keyword="python",
            secondary_keywords=["testing", "code"],
        )
        assert ctx.primary_keyword == "python"
        assert len(ctx.secondary_keywords) == 2


class TestOptimizationConfig:
    def test_defaults(self):
        c = OptimizationConfig()
        assert c.max_retries == 3
        assert c.temperature == 0.3
        assert c.cache_enabled is True

    def test_custom(self):
        c = OptimizationConfig(max_retries=5, temperature=0.1)
        assert c.max_retries == 5
        assert c.temperature == 0.1


class TestOptimizationResult:
    def test_defaults(self):
        r = OptimizationResult(section_index=0, section_heading="Test")
        assert r.status == OptimizationStatus.PENDING
        assert r.retries_used == 0
        assert r.rolled_back is False

    def test_with_data(self):
        r = OptimizationResult(
            section_index=1,
            section_heading="Introduction",
            section_type=SectionType.INTRODUCTION,
            status=OptimizationStatus.SUCCESS,
            content_before="Old content",
            content_after="New content",
            scores_before={"seo": 70.0},
            scores_after={"seo": 95.0},
            retries_used=2,
        )
        assert r.section_index == 1
        assert r.status == OptimizationStatus.SUCCESS
        assert r.retries_used == 2


class TestOptimizationReport:
    def test_defaults(self):
        r = OptimizationReport()
        assert r.total_sections == 0
        assert r.quality_gates_passed is False

    def test_with_data(self):
        r = OptimizationReport(
            project_id="proj_123",
            blog_title="Test Blog",
            total_sections=5,
            sections_optimized=3,
            sections_skipped=2,
        )
        assert r.project_id == "proj_123"
        assert r.sections_optimized == 3


class TestOptimizedSection:
    def test_defaults(self):
        s = OptimizedSection(section_index=0, heading="Test", original_content="", optimized_content="")
        assert s.status == OptimizationStatus.PENDING

    def test_equality_check(self):
        s = OptimizedSection(
            section_index=0,
            heading="Intro",
            original_content="Hello",
            optimized_content="Hello optimized",
            status=OptimizationStatus.SUCCESS,
        )
        assert s.optimized_content != s.original_content
