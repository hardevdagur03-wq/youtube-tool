"""Tests for OptimizationStage."""

from __future__ import annotations
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from orchestrator.stages.optimization_stage import OptimizationStage
from orchestrator.pipeline_context import PipelineContext
from orchestrator.stage_executor import StageResult


class TestOptimizationStage:
    def test_name(self):
        stage = OptimizationStage()
        assert stage.name == "optimization"

    def test_dependencies(self):
        stage = OptimizationStage()
        assert "merge" in stage.dependencies
        assert "review" in stage.dependencies

    @pytest.mark.asyncio
    async def test_validate_input_missing_merge(self):
        stage = OptimizationStage()
        ctx = PipelineContext()
        errors = await stage.validate_input(ctx)
        assert len(errors) > 0

    @pytest.mark.asyncio
    async def test_validate_input_missing_review(self):
        stage = OptimizationStage()
        ctx = PipelineContext()
        ctx.store_stage_output("merge", {"content": "Test content", "title": "Test"})
        errors = await stage.validate_input(ctx)
        assert len(errors) > 0

    @pytest.mark.asyncio
    async def test_validate_input_valid(self):
        stage = OptimizationStage()
        ctx = PipelineContext()
        ctx.store_stage_output("merge", {"content": "Test content", "title": "Test"})
        ctx.store_stage_output("review", {"report": {"quality_scores": {}, "issues": [], "recommendations": []}})
        errors = await stage.validate_input(ctx)
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_execute_no_project_dir(self):
        stage = OptimizationStage()
        ctx = PipelineContext(project_id="test")
        ctx.store_stage_output("merge", {"content": "# Test\n\nContent", "title": "Test"})
        ctx.store_stage_output("review", {"report": {"quality_scores": {}, "issues": [], "recommendations": []}})
        result = await stage.execute(ctx)
        assert isinstance(result, StageResult)
        assert result.success is True  # Even without optimization, it succeeds
