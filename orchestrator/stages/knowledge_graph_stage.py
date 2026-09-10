"""Knowledge Graph stage — builds the knowledge graph from existing artifacts.

Consumes metadata, transcript, analysis. Produces knowledge_graph.json.
No existing code is modified.
"""

from __future__ import annotations

import logging

from orchestrator.stage_executor import StageExecutor, StageResult
from orchestrator.pipeline_context import PipelineContext
from knowledge_graph.knowledge_graph_service import KnowledgeGraphService

logger = logging.getLogger(__name__)


class KnowledgeGraphStage(StageExecutor):
    """Builds a knowledge graph from existing metadata, transcript, and analysis."""

    @property
    def name(self) -> str:
        return "knowledge_graph"

    @property
    def dependencies(self) -> list[str]:
        return ["analysis"]

    async def validate_input(self, ctx: PipelineContext) -> list[str]:
        errors = []
        if not ctx.video_id and not ctx.project_id:
            errors.append("video_id or project_id required for knowledge graph stage")
        return errors

    async def execute(self, ctx: PipelineContext) -> StageResult:
        project_id = ctx.project_id
        metadata = ctx.get_stage_input("metadata")
        transcript = ctx.get_stage_input("transcript")
        analysis = ctx.get_stage_input("analysis")

        logger.info("Knowledge graph stage: building graph for project %s", project_id)

        svc = KnowledgeGraphService(
            project_manager=ctx.project_manager,
        )
        kg = svc.build(
            project_id=project_id,
            metadata=metadata,
            transcript=transcript,
            analysis=analysis,
        )

        summary = kg.summary

        return StageResult(
            success=True,
            stage=self.name,
            data=kg.model_dump(),
            warnings=kg.warnings,
        )
