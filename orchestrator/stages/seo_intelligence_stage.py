"""SEO Intelligence stage — builds SEO plan from knowledge graph and analysis.

Consumes knowledge_graph.json, analysis.json. Produces seo_plan.json.
No existing code is modified.
"""

from __future__ import annotations

import logging

from orchestrator.stage_executor import StageExecutor, StageResult
from orchestrator.pipeline_context import PipelineContext
from seo_intelligence.seo_service import SEOService

logger = logging.getLogger(__name__)


class SEOIntelligenceStage(StageExecutor):
    """Builds a complete SEO plan from the knowledge graph and analysis."""

    @property
    def name(self) -> str:
        return "seo_intelligence"

    @property
    def dependencies(self) -> list[str]:
        return ["knowledge_graph"]

    async def validate_input(self, ctx: PipelineContext) -> list[str]:
        errors = []
        if not ctx.project_id:
            errors.append("project_id required for SEO intelligence stage")
        return errors

    async def execute(self, ctx: PipelineContext) -> StageResult:
        project_id = ctx.project_id
        kg = ctx.get_stage_input("knowledge_graph")
        analysis = ctx.get_stage_input("analysis")
        metadata = ctx.get_stage_input("metadata")

        logger.info("SEO intelligence stage: building plan for project %s", project_id)

        svc = SEOService(
            project_manager=ctx.project_manager,
        )
        plan = svc.build(
            project_id=project_id,
            knowledge_graph=kg,
            analysis=analysis,
            metadata=metadata,
        )

        return StageResult(
            success=True,
            stage=self.name,
            data=plan.model_dump(),
            warnings=plan.warnings,
        )
