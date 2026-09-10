"""Progress Stream — real-time pipeline progress via SSE.

Emits progress events for each pipeline stage so clients can display
real-time progress bars, logs, and stage completion status.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from performance_engineering.streaming.sse_manager import SSEManager

logger = logging.getLogger(__name__)


class ProgressStream:
    """Real-time pipeline progress streaming.

    Emits events for: stage_started, stage_progress, stage_completed,
    stage_failed, pipeline_completed, pipeline_failed.
    """

    def __init__(self, sse_manager: SSEManager) -> None:
        self._sse = sse_manager
        self._total_stages: dict[str, int] = {}

    def set_total_stages(self, pipeline_id: str, total: int) -> None:
        """Set the total number of stages for a pipeline.

        Args:
            pipeline_id: Pipeline execution ID.
            total: Total stage count.
        """
        self._total_stages[pipeline_id] = total

    async def stage_started(self, pipeline_id: str, stage_name: str) -> int:
        """Emit a stage_started event.

        Args:
            pipeline_id: Pipeline execution ID.
            stage_name: Name of the stage.

        Returns:
            Number of subscribers that received the event.
        """
        return await self._sse.publish(
            pipeline_id,
            {"stage": stage_name, "action": "started", "progress_pct": 0.0},
            event_type="stage_started",
        )

    async def stage_progress(
        self, pipeline_id: str, stage_name: str, progress_pct: float, message: str = ""
    ) -> int:
        """Emit a stage_progress event.

        Args:
            pipeline_id: Pipeline execution ID.
            stage_name: Name of the stage.
            progress_pct: Progress percentage (0-100).
            message: Optional progress message.

        Returns:
            Number of subscribers.
        """
        return await self._sse.publish(
            pipeline_id,
            {
                "stage": stage_name,
                "action": "progress",
                "progress_pct": progress_pct,
                "message": message,
            },
            event_type="stage_progress",
        )

    async def stage_completed(
        self, pipeline_id: str, stage_name: str, duration_ms: float = 0.0
    ) -> int:
        """Emit a stage_completed event.

        Args:
            pipeline_id: Pipeline execution ID.
            stage_name: Name of the stage.
            duration_ms: Stage execution duration.

        Returns:
            Number of subscribers.
        """
        total = self._total_stages.get(pipeline_id, 1)
        completed_so_far = 0  # Tracked externally
        return await self._sse.publish(
            pipeline_id,
            {
                "stage": stage_name,
                "action": "completed",
                "duration_ms": duration_ms,
                "progress_pct": 0.0,
            },
            event_type="stage_completed",
        )

    async def stage_failed(
        self, pipeline_id: str, stage_name: str, error: str = ""
    ) -> int:
        """Emit a stage_failed event.

        Args:
            pipeline_id: Pipeline execution ID.
            stage_name: Name of the stage.
            error: Error message.

        Returns:
            Number of subscribers.
        """
        return await self._sse.publish(
            pipeline_id,
            {"stage": stage_name, "action": "failed", "error": error},
            event_type="stage_failed",
        )

    async def pipeline_completed(
        self, pipeline_id: str, duration_ms: float = 0.0
    ) -> int:
        """Emit a pipeline_completed event.

        Args:
            pipeline_id: Pipeline execution ID.
            duration_ms: Total pipeline duration.

        Returns:
            Number of subscribers.
        """
        return await self._sse.publish(
            pipeline_id,
            {"action": "completed", "duration_ms": duration_ms, "progress_pct": 100.0},
            event_type="pipeline_completed",
        )

    async def pipeline_failed(
        self, pipeline_id: str, error: str = ""
    ) -> int:
        """Emit a pipeline_failed event.

        Args:
            pipeline_id: Pipeline execution ID.
            error: Error message.

        Returns:
            Number of subscribers.
        """
        return await self._sse.publish(
            pipeline_id,
            {"action": "failed", "error": error},
            event_type="pipeline_failed",
        )

    async def stream_transcript(
        self, pipeline_id: str, segment_text: str, segment_index: int
    ) -> int:
        """Emit streaming transcript output.

        Args:
            pipeline_id: Pipeline execution ID.
            segment_text: Transcript segment text.
            segment_index: Segment index.

        Returns:
            Number of subscribers.
        """
        return await self._sse.publish(
            pipeline_id,
            {
                "action": "transcript_segment",
                "text": segment_text,
                "index": segment_index,
            },
            event_type="transcript",
        )
