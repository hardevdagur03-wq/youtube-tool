"""Throughput Optimizer — worker scaling and queue depth management.

Monitors queue depths and optimizes worker allocation.
Recommends scaling actions based on throughput analysis.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any

from performance_engineering.config import PerformanceConfig

logger = logging.getLogger(__name__)


class ThroughputOptimizer:
    """Monitors and optimizes queue throughput.

    Tracks queue depths, processing rates, and recommends
    worker scaling actions based on observed throughput.
    """

    def __init__(self, config: PerformanceConfig | None = None) -> None:
        self._config = config or PerformanceConfig.from_env()
        self._queue_depths: dict[str, list[tuple[float, int]]] = defaultdict(list)
        self._processing_rates: dict[str, list[float]] = defaultdict(list)
        self._max_depth_history = 100

    def record_queue_depth(self, queue: str, depth: int) -> None:
        """Record a queue depth observation.

        Args:
            queue: Queue name.
            depth: Current queue depth.
        """
        self._queue_depths[queue].append((time.time(), depth))
        if len(self._queue_depths[queue]) > self._max_depth_history:
            self._queue_depths[queue].pop(0)

    def record_processing_rate(self, queue: str, tasks_per_second: float) -> None:
        """Record a processing rate observation.

        Args:
            queue: Queue name.
            tasks_per_second: Observed processing rate.
        """
        self._processing_rates[queue].append(tasks_per_second)
        if len(self._processing_rates[queue]) > self._max_depth_history:
            self._processing_rates[queue].pop(0)

    def get_average_depth(self, queue: str, window_seconds: int = 60) -> float:
        """Get the average queue depth over a time window.

        Args:
            queue: Queue name.
            window_seconds: Time window in seconds.

        Returns:
            Average depth.
        """
        now = time.time()
        cutoff = now - window_seconds
        depths = [
            d for t, d in self._queue_depths.get(queue, []) if t >= cutoff
        ]
        if not depths:
            return 0.0
        return sum(depths) / len(depths)

    def get_processing_rate(self, queue: str, window_seconds: int = 60) -> float:
        """Get the average processing rate for a queue.

        Args:
            queue: Queue name.
            window_seconds: Time window in seconds.

        Returns:
            Average tasks/second.
        """
        now = time.time()
        cutoff = now - window_seconds
        depths_at_cutoff = [
            d for t, d in self._queue_depths.get(queue, [])
            if t >= cutoff
        ]
        if not depths_at_cutoff or len(depths_at_cutoff) < 2:
            return 0.0

        # Calculate rate as depth change over time
        first_depth = depths_at_cutoff[0]
        last_depth = depths_at_cutoff[-1]
        depth_change = first_depth - last_depth
        return max(0, depth_change / min(window_seconds, now - cutoff + 1))

    def recommend_scale(self, queue: str) -> dict[str, Any]:
        """Recommend scaling action for a queue.

        Args:
            queue: Queue name.

        Returns:
            Dict with scaling recommendation.
        """
        avg_depth = self.get_average_depth(queue)
        processing_rate = self.get_processing_rate(queue)

        recommendation = "maintain"
        workers_needed = 1

        if avg_depth > 100 and processing_rate < 1.0:
            recommendation = "scale_up"
            workers_needed = max(2, int(avg_depth / 50))
        elif avg_depth < 5 and processing_rate > 10:
            recommendation = "scale_down"
            workers_needed = 1

        return {
            "queue": queue,
            "avg_depth": round(avg_depth, 1),
            "processing_rate": round(processing_rate, 2),
            "recommendation": recommendation,
            "workers_needed": workers_needed,
        }

    def get_summary(self) -> dict[str, Any]:
        """Get throughput summary for all queues.

        Returns:
            Dict of queue -> summary stats.
        """
        queues = set(self._queue_depths.keys()) | set(self._processing_rates.keys())
        return {
            queue: self.recommend_scale(queue)
            for queue in sorted(queues)
        }
