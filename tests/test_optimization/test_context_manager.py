"""Tests for OptimizationContextManager."""

from __future__ import annotations
import json
import tempfile
import os
from optimization.context_manager import OptimizationContextManager
from optimization.optimization_models import OptimizationType, SectionType


SAMPLE_ISSUES = [
    {"description": "Low keyword density for 'python'", "location": "Introduction", "severity": "medium"},
    {"description": "Passive voice detected in conclusion", "location": "Conclusion", "severity": "low"},
    {"description": "Grammar error in sentence", "location": "Body Section 1", "severity": "high"},
]

SAMPLE_RECOMMENDATIONS = [
    {"description": "Add primary keyword to introduction", "priority": "must_fix", "category": "seo"},
    {"description": "Fix passive voice in conclusion", "priority": "should_improve", "category": "grammar"},
]


class TestOptimizationContextManager:
    def test_init(self):
        cm = OptimizationContextManager()
        assert cm is not None

    def test_build_context_minimal(self):
        cm = OptimizationContextManager()
        ctx = cm.build_context(
            section_index=0,
            section_text="Hello world",
            section_heading="Introduction",
            section_type=SectionType.INTRODUCTION,
            optimization_types=[OptimizationType.SEO],
            artifacts={},
        )
        assert ctx.section_text == "Hello world"
        assert ctx.section_heading == "Introduction"
        assert ctx.section_type == SectionType.INTRODUCTION

    def test_build_context_with_artifacts(self):
        cm = OptimizationContextManager()
        artifacts = {
            "seo_plan": {"keyword_strategy": {"primary": "python", "secondary": ["code", "testing"]}},
            "knowledge_graph": {"facts": [{"statement": "Python is a programming language"}]},
            "outline": {"sections": [{"heading": "Introduction", "description": "Overview of Python"}]},
            "review_report": {
                "quality_scores": {"seo": 75.0, "grammar": 88.0},
                "issues": SAMPLE_ISSUES,
                "recommendations": SAMPLE_RECOMMENDATIONS,
            },
        }
        ctx = cm.build_context(
            section_index=0,
            section_text="Test content about python.",
            section_heading="Introduction",
            section_type=SectionType.INTRODUCTION,
            optimization_types=[OptimizationType.SEO, OptimizationType.GRAMMAR],
            artifacts=artifacts,
        )
        assert ctx.primary_keyword == "python"
        assert len(ctx.secondary_keywords) == 2

    def test_filter_relevant_issues(self):
        cm = OptimizationContextManager()
        relevant = cm._filter_relevant_issues("Introduction", "Python is great", SAMPLE_ISSUES)
        assert len(relevant) >= 1

    def test_filter_relevant_issues_empty(self):
        cm = OptimizationContextManager()
        relevant = cm._filter_relevant_issues("Test", "Content", [])
        assert relevant == []

    def test_find_outline_section(self):
        cm = OptimizationContextManager()
        outline = {"sections": [{"heading": "Introduction", "description": "Start here"}, {"heading": "Body", "description": "Main content"}]}
        found = cm._find_outline_section("# Introduction", outline)
        assert found.get("heading") == "Introduction"

    def test_find_outline_section_no_match(self):
        cm = OptimizationContextManager()
        outline = {"sections": [{"heading": "Introduction"}]}
        found = cm._find_outline_section("Nonexistent", outline)
        assert found == {}

    def test_load_artifacts_nonexistent_dir(self):
        cm = OptimizationContextManager()
        artifacts = cm.load_artifacts("/nonexistent/path")
        assert artifacts == {}

    def test_load_artifacts_from_directory(self):
        cm = OptimizationContextManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "outline.json"), "w") as f:
                json.dump({"sections": []}, f)
            with open(os.path.join(tmpdir, "seo_plan.json"), "w") as f:
                json.dump({"keyword_strategy": {"primary": "test"}}, f)
            artifacts = cm.load_artifacts(tmpdir)
            assert "outline" in artifacts
            assert "seo_plan" in artifacts

    def test_clear_cache(self):
        cm = OptimizationContextManager()
        cm._artifacts["test"] = "value"
        cm.clear_cache()
        assert cm._artifacts == {}
