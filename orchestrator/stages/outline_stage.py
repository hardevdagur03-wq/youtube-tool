"""Outline stage — generates blog outline from analysis and transcript.

No existing code is modified.
"""

from __future__ import annotations

import logging

from orchestrator.stage_executor import StageExecutor, StageResult
from orchestrator.pipeline_context import PipelineContext

logger = logging.getLogger(__name__)


class OutlineStage(StageExecutor):
    """Generates blog outline from existing analysis data."""

    @property
    def name(self) -> str:
        return "outline"

    @property
    def dependencies(self) -> list[str]:
        return ["seo"]

    async def validate_input(self, ctx: PipelineContext) -> list[str]:
        errors = []
        analysis = ctx.get_stage_input("analysis")
        if not analysis:
            errors.append("analysis data required for outline generation")
        return errors

    async def execute(self, ctx: PipelineContext) -> StageResult:
        analysis = ctx.get_stage_input("analysis")
        transcript = ctx.get_stage_input("transcript")

        outline_data = analysis.get("outline", {}) if isinstance(analysis, dict) else {}
        if not outline_data:
            sections = analysis.get("outline", {}).get("sections", []) if isinstance(analysis, dict) else []
            outline_data = {"sections": sections}

        return StageResult(
            success=True,
            stage=self.name,
            data={
                "outline": outline_data,
                "sections_count": len(outline_data.get("sections", [])) if isinstance(outline_data, dict) else 0,
            },
        )
