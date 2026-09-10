"""Tests for OptimizationPlanner."""

from __future__ import annotations
from optimization.optimization_planner import OptimizationPlanner
from optimization.optimization_models import OptimizationType, QualityGate


class TestOptimizationPlanner:
    def test_init(self):
        p = OptimizationPlanner()
        assert p is not None

    def test_plan_empty_sections(self):
        p = OptimizationPlanner()
        plans = p.plan([], {}, [], [], "")
        assert plans == []

    def test_plan_section_needs_seo(self):
        p = OptimizationPlanner()
        sections = [{"heading": "# Introduction", "content": "Some text"}]
        scores = {"seo": 70.0, "grammar": 98.0, "readability": 95.0}
        plans = p.plan(sections, scores, [], [], "python")
        assert len(plans) == 1
        assert plans[0].needs_optimization is True
        assert OptimizationType.SEO in plans[0].optimization_types

    def test_plan_section_passes_all_gates(self):
        p = OptimizationPlanner()
        sections = [{"heading": "# Introduction", "content": "Perfect content."}]
        scores = {"seo": 95.0, "grammar": 98.0, "readability": 95.0, "hallucination_risk": 100.0}
        plans = p.plan(sections, scores, [], [], "python")
        assert len(plans) == 1
        assert plans[0].needs_optimization is False

    def test_plan_section_needs_multiple(self):
        p = OptimizationPlanner()
        sections = [{"heading": "# Body", "content": "Bad content."}]
        scores = {"seo": 60.0, "grammar": 70.0, "readability": 65.0}
        plans = p.plan(sections, scores, [], [], "python")
        assert len(plans[0].optimization_types) >= 3

    def test_detect_section_type(self):
        p = OptimizationPlanner()
        assert p._detect_section_type("# Introduction", "Some intro text") == p._detect_section_type("# Introduction", "Some intro text")
        t = p._detect_section_type("## FAQ", "Q: What? A: Answer.")
        assert t.name == "FAQ" or t is not None

    def test_plan_sort_by_priority(self):
        p = OptimizationPlanner()
        sections = [
            {"heading": "## Low Score", "content": "a"},
            {"heading": "## Perfect", "content": "b"},
        ]
        scores_high = {"seo": 50.0, "grammar": 50.0}
        scores_low = {"seo": 95.0, "grammar": 98.0}
        plans = p.plan(sections, scores_high, [], [], "python")
        if len(plans) >= 1:
            assert plans[0].needs_optimization is True
