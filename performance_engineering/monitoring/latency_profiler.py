"""Latency Profiler — per-stage latency breakdown and performance profiling.

Context manager for profiling individual pipeline stages.
Generates flamegraph-compatible output for performance analysis.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Generator

from performance_engineering.models import StageTiming

logger = logging.getLogger(__name__)


class LatencyProfiler:
    """Per-stage latency profiler.

    Records stage execution time, queue time, and provider latency.
    Provides breakdown reports and alerting on slow operations.

    Usage::

        profiler = LatencyProfiler()
        with profiler.profile("transcript"):
            transcript = service.get_transcript(video_id)
    """

    def __init__(self, slow_threshold_ms: float = 1000.0) -> None:
        self._slow_threshold = slow_threshold_ms
        self._timings: dict[str, list[StageTiming]] = {}
        self._current_stage: str = ""

    @contextmanager
    def profile(self, stage_name: str) -> Generator[None, None, None]:
        """Profile a stage execution.

        Args:
            stage_name: Stage name to profile.

        Yields:
            None.
        """
        previous_stage = self._current_stage
        self._current_stage = stage_name

        timing = StageTiming(stage_name=stage_name)
        start = time.time()

        try:
            yield
            timing.duration_ms = (time.time() - start) * 1000
            timing.processing_time_ms = timing.duration_ms
        except Exception as exc:
            timing.duration_ms = (time.time() - start) * 1000
            timing.error = str(exc)[:200]

        if stage_name not in self._timings:
            self._timings[stage_name] = []
        self._timings[stage_name].append(timing)

        if timing.duration_ms > self._slow_threshold:
            logger.warning(
                "SLOW STAGE: %s took %.0fms (threshold: %.0fms)",
                stage_name, timing.duration_ms, self._slow_threshold,
            )

        self._current_stage = previous_stage

    def record_queue_time(self, stage_name: str, queue_time_ms: float) -> None:
        """Record queue wait time for a stage.

        Args:
            stage_name: Stage name.
            queue_time_ms: Queue time in ms.
        """
        timings = self._timings.get(stage_name, [])
        if timings:
            timings[-1].queue_time_ms = queue_time_ms

    def record_provider_latency(
        self, stage_name: str, provider_latency_ms: float
    ) -> None:
        """Record provider latency for a stage.

        Args:
            stage_name: Stage name.
            provider_latency_ms: Provider latency in ms.
        """
        timings = self._timings.get(stage_name, [])
        if timings:
            timings[-1].provider_latency_ms = provider_latency_ms

    def get_timing_summary(self, stage_name: str) -> dict[str, float]:
        """Get timing summary for a stage.

        Args:
            stage_name: Stage name.

        Returns:
            Dict with avg, max, min, p95, count.
        """
        timings = [t.duration_ms for t in self._timings.get(stage_name, [])]
        if not timings:
            return {}
        sorted_t = sorted(timings)
        n = len(sorted_t)
        return {
            "avg_ms": round(sum(sorted_t) / n, 1),
            "min_ms": round(sorted_t[0], 1),
            "max_ms": round(sorted_t[-1], 1),
            "p95_ms": round(sorted_t[int(n * 0.95)], 1),
            "count": n,
        }

    def get_all_summaries(self) -> dict[str, dict[str, float]]:
        """Get timing summaries for all stages.

        Returns:
            Dict of stage_name -> summary.
        """
        return {
            stage: self.get_timing_summary(stage)
            for stage in sorted(self._timings.keys())
        }

    def get_slow_stages(self) -> list[dict[str, Any]]:
        """Get stages that exceeded the slow threshold.

        Returns:
            List of slow stage records.
        """
        slow = []
        for stage_name, timings in self._timings.items():
            for t in timings[-10:]:  # Last 10
                if t.duration_ms > self._slow_threshold:
                    slow.append({
                        "stage": stage_name,
                        "duration_ms": round(t.duration_ms, 1),
                        "error": t.error,
                    })
        return slow

    def reset(self) -> None:
        """Clear all profiled timings."""
        self._timings.clear()
