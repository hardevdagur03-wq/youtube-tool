"""SEO stage — wraps existing SEOService.

No existing code is modified.
"""

from __future__ import annotations

import json
import logging

from orchestrator.stage_executor import StageExecutor, StageResult
from orchestrator.pipeline_context import PipelineContext
from modules.seo.seo_service import SEOService

logger = logging.getLogger(__name__)


class SEOStage(StageExecutor):
    """Runs SEO optimization using the existing SEOService."""

    @property
    def name(self) -> str:
        return "seo"

    @property
    def dependencies(self) -> list[str]:
        return ["analysis"]

    async def validate_input(self, ctx: PipelineContext) -> list[str]:
        errors = []
        if not ctx.video_id:
            errors.append("video_id required for SEO stage")
        return errors

    async def execute(self, ctx: PipelineContext) -> StageResult:
        video_id = ctx.video_id
        analysis = ctx.get_stage_input("analysis")
        metadata = ctx.get_stage_input("metadata")

        logger.info("SEO stage: optimizing SEO for video %s", video_id)

        service = SEOService()
        result = service.optimize(
            blog_data={},
            video_id=video_id,
            metadata=metadata,
            analysis=analysis,
        )

        data = json.loads(result.model_dump_json()) if hasattr(result, "model_dump_json") else {}
        return StageResult(
            success=True,
            stage=self.name,
            data=data,
        )
