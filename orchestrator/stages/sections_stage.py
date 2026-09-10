"""Sections stage — generates blog sections from outline.

No existing code is modified.
"""

from __future__ import annotations

import logging

from orchestrator.stage_executor import StageExecutor, StageResult
from orchestrator.pipeline_context import PipelineContext

logger = logging.getLogger(__name__)


class SectionsStage(StageExecutor):
    """Generates blog content sections from outline."""

    @property
    def name(self) -> str:
        return "sections"

    @property
    def dependencies(self) -> list[str]:
        return ["outline"]

    async def validate_input(self, ctx: PipelineContext) -> list[str]:
        errors = []
        outline = ctx.get_stage_input("outline")
        if not outline:
            errors.append("outline data required for section generation")
        return errors

    async def execute(self, ctx: PipelineContext) -> StageResult:
        outline = ctx.get_stage_input("outline")
        transcript = ctx.get_stage_input("transcript")

        section_list = []
        raw_sections = []
        if isinstance(outline, dict):
            raw_sections = outline.get("outline", {}).get("sections", [])
        if not raw_sections:
            raw_sections = ["Introduction", "Main Content", "Conclusion"]

        for i, section in enumerate(raw_sections):
            title = section if isinstance(section, str) else section.get("title", f"Section {i+1}")
            section_list.append({
                "id": f"section_{i+1}",
                "title": title,
                "content": "",
                "order": i + 1,
            })

        return StageResult(
            success=True,
            stage=self.name,
            data={
                "sections": section_list,
                "total_sections": len(section_list),
            },
        )
