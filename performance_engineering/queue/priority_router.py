"""Queue Priority Router — AI-specific queue routing and prioritization.

Routes pipeline stages to the appropriate priority queues based on
stage type. Integrates with existing background_processing queues.
"""

from __future__ import annotations

import logging
from typing import Any

from performance_engineering.config import PerformanceConfig

logger = logging.getLogger(__name__)

# Default queue mapping: stage -> (queue_name, priority)
_DEFAULT_QUEUE_MAP: dict[str, tuple[str, int]] = {
    "metadata": ("high", 5),
    "transcript": ("high", 5),
    "analysis": ("ai_critical", 10),
    "knowledge_graph": ("ai_normal", 7),
    "seo": ("ai_normal", 7),
    "seo_intelligence": ("ai_normal", 7),
    "outline": ("ai_normal", 7),
    "sections": ("ai_normal", 7),
    "review": ("ai_normal", 7),
    "export": ("export", 3),
    "publishing": ("publishing", 3),
    "optimization": ("ai_critical", 10),
}


class PriorityRouter:
    """Routes pipeline stages to appropriate priority queues.

    Maps each stage type to a queue and priority level.
    Supports dynamic queue assignment and override configuration.
    """

    def __init__(self, config: PerformanceConfig | None = None) -> None:
        self._config = config or PerformanceConfig.from_env()
        self._queue_map = dict(_DEFAULT_QUEUE_MAP)

    def get_queue(self, stage_name: str) -> str:
        """Get the queue name for a stage.

        Args:
            stage_name: Stage name.

        Returns:
            Queue name string.
        """
        return self._queue_map.get(stage_name, ("default", 1))[0]

    def get_priority(self, stage_name: str) -> int:
        """Get the priority level for a stage.

        Args:
            stage_name: Stage name.

        Returns:
            Priority level (1-10, higher = more urgent).
        """
        return self._queue_map.get(stage_name, ("default", 1))[1]

    def set_queue(self, stage_name: str, queue: str, priority: int = 5) -> None:
        """Override the queue assignment for a stage.

        Args:
            stage_name: Stage name.
            queue: Queue name.
            priority: Priority level.
        """
        self._queue_map[stage_name] = (queue, priority)

    def get_queue_map(self) -> dict[str, dict[str, Any]]:
        """Get the full queue mapping.

        Returns:
            Dict of stage_name -> {queue, priority}.
        """
        return {
            stage: {"queue": q, "priority": p}
            for stage, (q, p) in self._queue_map.items()
        }

    def get_stages_for_queue(self, queue: str) -> list[str]:
        """Get all stages assigned to a queue.

        Args:
            queue: Queue name.

        Returns:
            List of stage names.
        """
        return [
            stage for stage, (q, _) in self._queue_map.items() if q == queue
        ]

    def get_queue_load_summary(self) -> dict[str, int]:
        """Get the number of stages per queue.

        Returns:
            Dict of queue_name -> stage_count.
        """
        summary: dict[str, int] = {}
        for _, (q, _) in self._queue_map.items():
            summary[q] = summary.get(q, 0) + 1
        return summary
