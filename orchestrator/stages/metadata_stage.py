"""Metadata stage — wraps existing YouTubeMetadataService.

No existing code is modified.
"""

from __future__ import annotations

import logging

from orchestrator.stage_executor import StageExecutor, StageResult
from orchestrator.pipeline_context import PipelineContext
from services.youtube_metadata_service import YouTubeMetadataService

logger = logging.getLogger(__name__)


class MetadataStage(StageExecutor):
    """Fetches video metadata using the existing YouTubeMetadataService."""

    @property
    def name(self) -> str:
        return "metadata"

    @property
    def dependencies(self) -> list[str]:
        return []

    async def validate_input(self, ctx: PipelineContext) -> list[str]:
        errors = []
        if not ctx.video_id:
            errors.append("video_id is required for metadata stage")
        return errors

    async def execute(self, ctx: PipelineContext) -> StageResult:
        video_id = ctx.video_id
        logger.info("Metadata stage: fetching metadata for video %s", video_id)

        service = YouTubeMetadataService()
        response = service.get_metadata(video_id)

        if not response.success:
            return StageResult(
                success=False,
                stage=self.name,
                error=response.error or "Failed to fetch metadata",
            )

        data = response.model_dump() if hasattr(response, "model_dump") else {}
        return StageResult(
            success=True,
            stage=self.name,
            data=data,
        )
