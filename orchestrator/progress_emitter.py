"""Progress Emitter — real-time progress events for pipeline execution.

No existing code is modified.
"""

from __future__ import annotations

import time
from typing import Any

from orchestrator.pipeline_events import EventBus, PipelineEvent, PipelineEventType
from orchestrator.pipeline_state import StageState, StageInfo


class ProgressEmitter:
    """Emits real-time progress events during pipeline execution."""

    def __init__(self, event_bus: EventBus, project_id: str) -> None:
        self._bus = event_bus
        self._project_id = project_id
        self._stage_start_times: dict[str, float] = {}
        self._total_stages = 0
        self._completed_stages = 0

    def set_total_stages(self, total: int) -> None:
        self._total_stages = total

    async def emit_pipeline_started(self) -> None:
        await self._bus.emit(PipelineEvent(
            type=PipelineEventType.PIPELINE_STARTED,
            project_id=self._project_id,
            message="Pipeline started",
            data={"total_stages": self._total_stages},
        ))

    async def emit_pipeline_completed(self, metrics: dict[str, Any] | None = None) -> None:
        await self._bus.emit(PipelineEvent(
            type=PipelineEventType.PIPELINE_COMPLETED,
            project_id=self._project_id,
            message="Pipeline completed successfully",
            data=metrics or {},
        ))

    async def emit_pipeline_failed(self, error: str) -> None:
        await self._bus.emit(PipelineEvent(
            type=PipelineEventType.PIPELINE_FAILED,
            project_id=self._project_id,
            message=error,
        ))

    async def emit_stage_started(self, stage: str) -> None:
        self._stage_start_times[stage] = time.time()
        await self._bus.emit(PipelineEvent(
            type=PipelineEventType.STAGE_STARTED,
            project_id=self._project_id,
            stage=stage,
            message=f"Stage started: {stage}",
        ))

    async def emit_stage_completed(self, stage: str, info: StageInfo | None = None) -> None:
        self._completed_stages += 1
        pct = round((self._completed_stages / max(self._total_stages, 1)) * 100, 1)
        await self._bus.emit(PipelineEvent(
            type=PipelineEventType.STAGE_COMPLETED,
            project_id=self._project_id,
            stage=stage,
            message=f"Stage completed: {stage}",
            data={
                "progress_pct": pct,
                "completed": self._completed_stages,
                "total": self._total_stages,
                "duration": round(time.time() - self._stage_start_times.get(stage, time.time()), 3),
                "stage_info": info.to_dict() if info else {},
            },
        ))

    async def emit_stage_failed(self, stage: str, error: str) -> None:
        await self._bus.emit(PipelineEvent(
            type=PipelineEventType.STAGE_FAILED,
            project_id=self._project_id,
            stage=stage,
            message=f"Stage failed: {stage}",
            data={"error": error},
        ))

    async def emit_stage_retrying(self, stage: str, attempt: int, max_retries: int, delay: float) -> None:
        await self._bus.emit(PipelineEvent(
            type=PipelineEventType.STAGE_RETRYING,
            project_id=self._project_id,
            stage=stage,
            message=f"Retrying stage: {stage} (attempt {attempt}/{max_retries})",
            data={"attempt": attempt, "max_retries": max_retries, "delay": delay},
        ))

    async def emit_progress(self, pct: float, stage: str, detail: str = "") -> None:
        await self._bus.emit(PipelineEvent(
            type=PipelineEventType.PROGRESS_UPDATED,
            project_id=self._project_id,
            stage=stage,
            message=detail,
            data={"progress_pct": pct},
        ))

    async def emit_checkpoint(self, stage: str) -> None:
        await self._bus.emit(PipelineEvent(
            type=PipelineEventType.CHECKPOINT_CREATED,
            project_id=self._project_id,
            stage=stage,
            message=f"Checkpoint created after: {stage}",
        ))
