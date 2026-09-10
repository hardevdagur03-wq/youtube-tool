"""Tests for OptimizationService."""

from __future__ import annotations
import json
import tempfile
import os
from unittest.mock import MagicMock
from optimization.optimization_service import OptimizationService
from optimization.optimization_models import OptimizationConfig


SAMPLE_DRAFT = """# Test Blog

## Introduction

This is a test introduction.

## Body

This is the body content.

## Conclusion

This is the conclusion.
"""


class TestOptimizationService:
    def test_init(self):
        s = OptimizationService()
        assert s is not None

    def test_optimize_from_artifacts(self):
        s = OptimizationService()
        draft, report = s.optimize_from_artifacts(
            draft_md=SAMPLE_DRAFT,
            review_report={
                "metadata": {"blog_title": "Test Blog"},
                "quality_scores": {"seo": 70.0, "grammar": 80.0, "readability": 75.0},
                "issues": [],
                "recommendations": [],
            },
            outline={"sections": []},
            seo_plan={"keyword_strategy": {"primary": "test"}},
            knowledge_graph={},
            project={"project_id": "test_proj"},
        )
        assert isinstance(draft, str)
        assert draft == SAMPLE_DRAFT  # No LLM, no changes

    def test_optimize_from_project_missing_dir(self):
        s = OptimizationService()
        draft, report = s.optimize_from_project(
            project_dir="/nonexistent/path",
        )
        assert draft is None
        assert report is None  # No draft found

    def test_optimize_from_project_with_files(self):
        s = OptimizationService()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create required files
            with open(os.path.join(tmpdir, "draft.md"), "w") as f:
                f.write(SAMPLE_DRAFT)
            with open(os.path.join(tmpdir, "review_report.json"), "w") as f:
                json.dump({"metadata": {"blog_title": "Test"}, "quality_scores": {}, "issues": [], "recommendations": []}, f)
            with open(os.path.join(tmpdir, "outline.json"), "w") as f:
                json.dump({"sections": []}, f)
            with open(os.path.join(tmpdir, "seo_plan.json"), "w") as f:
                json.dump({"keyword_strategy": {"primary": "test"}}, f)
            with open(os.path.join(tmpdir, "knowledge_graph.json"), "w") as f:
                json.dump({"facts": []}, f)
            with open(os.path.join(tmpdir, "project.json"), "w") as f:
                json.dump({"project_id": "test_proj"}, f)

            draft, report = s.optimize_from_project(project_dir=tmpdir)
            assert draft is not None
            assert report is not None
