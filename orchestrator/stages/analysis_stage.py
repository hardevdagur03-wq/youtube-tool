"""Analysis stage — wraps existing ContentAnalysisService.

No existing code is modified.
"""

from __future__ import annotations

import json
import logging

from orchestrator.stage_executor import StageExecutor, StageResult
from orchestrator.pipeline_context import PipelineContext
from services.content_analysis_service import ContentAnalysisService

logger = logging.getLogger(__name__)


class AnalysisStage(StageExecutor):
    """Runs AI content analysis using the existing ContentAnalysisService."""

    @property
    def name(self) -> str:
        return "analysis"

    @property
    def dependencies(self) -> list[str]:
        return ["transcript"]

    async def validate_input(self, ctx: PipelineContext) -> list[str]:
        errors = []
        transcript = ctx.get_stage_input("transcript")
        if not transcript:
            errors.append("transcript data required for analysis")
        return errors

    async def execute(self, ctx: PipelineContext) -> StageResult:
        video_id = ctx.video_id
        transcript = ctx.get_stage_input("transcript")
        plain_text = ""
        if isinstance(transcript, dict):
            plain_text = transcript.get("plain_text", "") or transcript.get("text", "")

        logger.info("Analysis stage: analyzing transcript for video %s", video_id)

        service = ContentAnalysisService()
        result = service.analyze(
            transcript=plain_text,
            video_id=video_id,
        )

        if not result.success:
            return StageResult(
                success=False,
                stage=self.name,
                error=result.error or "Analysis failed",
            )

        data = json.loads(result.model_dump_json()) if hasattr(result, "model_dump_json") else {}
        return StageResult(
            success=True,
            stage=self.name,
            data=data,
        )
