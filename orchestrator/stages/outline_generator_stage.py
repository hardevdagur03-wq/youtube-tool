"""Outline Generator stage — builds content outline from KG and SEO plan.

No existing code is modified.
"""

from __future__ import annotations

import logging

from orchestrator.stage_executor import StageExecutor, StageResult
from orchestrator.pipeline_context import PipelineContext
from outline_generator.outline_service import OutlineService

logger = logging.getLogger(__name__)


class OutlineGeneratorStage(StageExecutor):
    """Builds a complete content outline blueprint."""

    @property
    def name(self) -> str:
        return "outline_generator"

    @property
    def dependencies(self) -> list[str]:
        return ["seo_intelligence"]

    async def validate_input(self, ctx: PipelineContext) -> list[str]:
        errors = []
        if not ctx.project_id:
            errors.append("project_id required for outline generator stage")
        return errors

    async def execute(self, ctx: PipelineContext) -> StageResult:
        project_id = ctx.project_id
        kg = ctx.get_stage_input("knowledge_graph")
        seo_plan = ctx.get_stage_input("seo_intelligence")
        analysis = ctx.get_stage_input("analysis")
        metadata = ctx.get_stage_input("metadata")

        logger.info("Outline generator stage: building outline for project %s", project_id)

        svc = OutlineService(project_manager=ctx.project_manager)
        outline = svc.build(
            project_id=project_id,
            knowledge_graph=kg,
            seo_plan=seo_plan,
            analysis=analysis,
            metadata=metadata,
        )

        return StageResult(
            success=True,
            stage=self.name,
            data=outline.model_dump(),
            warnings=outline.warnings,
        )
