"""Transcript stage — uses TranscriptManager from the Transcript Reliability Engine.

Wraps the new TranscriptManager with automatic failover, circuit breaker,
provider priority, and zero pipeline crashes on failure.
"""

from __future__ import annotations

import logging

from orchestrator.stage_executor import StageExecutor, StageResult
from orchestrator.pipeline_context import PipelineContext
from transcript_reliability import TranscriptManager
from transcript_reliability.providers import get_default_providers

logger = logging.getLogger(__name__)


class TranscriptStage(StageExecutor):
    """Fetches transcript using the TranscriptManager."""

    def __init__(self, transcript_manager: TranscriptManager | None = None) -> None:
        self._manager = transcript_manager or self._create_default_manager()

    @staticmethod
    def _create_default_manager() -> TranscriptManager:
        manager = TranscriptManager()
        for provider in get_default_providers():
            manager.register_provider(provider)
        logger.info("TranscriptStage initialized with %d providers", len(get_default_providers()))
        return manager

    @property
    def name(self) -> str:
        return "transcript"

    @property
    def dependencies(self) -> list[str]:
        return ["metadata"]

    async def validate_input(self, ctx: PipelineContext) -> list[str]:
        errors = []
        if not ctx.video_id:
            errors.append("video_id is required for transcript stage")
        return errors

    async def execute(self, ctx: PipelineContext) -> StageResult:
        video_id = ctx.video_id
        logger.info("Transcript stage: fetching transcript for video %s", video_id)

        result = self._manager.get_transcript(video_id=video_id)

        if not result.success:
            logger.warning(
                "Transcript stage: all providers failed for %s: %s",
                video_id, result.error,
            )
            # Stage FAILURE does NOT crash the pipeline — return as failed stage
            return StageResult(
                success=False,
                stage=self.name,
                error=result.error or "No transcript available from any provider",
            )

        data = result.model_dump() if hasattr(result, "model_dump") else {}
        logger.info(
            "Transcript stage: obtained transcript for %s (words=%d, source=%s)",
            video_id, result.word_count, result.source.value if hasattr(result.source, 'value') else result.source,
        )
        return StageResult(
            success=True,
            stage=self.name,
            data=data,
        )
