"""Pipeline Metrics — comprehensive instrumentation for every pipeline stage.

Tracks:
- Pipeline started/completed/failed counts
- Per-stage duration (histogram)
- Retry counts per stage
- Checkpoint saves and resumes
- Pipeline queue time
- Stage-level success/failure rates
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from prometheus_client import Counter, Gauge, Histogram

from observability.logger import get_logger

logger = get_logger(__name__)

PREFIX = "youtube_seo_pipeline"

# Counters
pipeline_started = Counter(f"{PREFIX}_started_total", "Total pipelines started", ["project_id", "pipeline_type"])
pipeline_completed = Counter(f"{PREFIX}_completed_total", "Total pipelines completed", ["project_id", "pipeline_type"])
pipeline_failed = Counter(f"{PREFIX}_failed_total", "Total pipelines failed", ["project_id", "pipeline_type", "stage"])
pipeline_retried = Counter(f"{PREFIX}_retried_total", "Pipeline stage retries", ["stage"])
pipeline_resumed = Counter(f"{PREFIX}_resumed_total", "Pipeline resumes from checkpoint", ["project_id"])
pipeline_checkpoint = Counter(f"{PREFIX}_checkpoint_total", "Pipeline checkpoints saved", ["stage"])

# Histograms
pipeline_duration = Histogram(
    f"{PREFIX}_duration_seconds",
    "Pipeline duration in seconds",
    ["pipeline_type"],
    buckets=(30, 60, 120, 300, 600, 1800, 3600, 7200),
)
stage_duration = Histogram(
    f"{PREFIX}_stage_duration_seconds",
    "Per-stage duration in seconds",
    ["stage", "pipeline_type"],
    buckets=(5, 10, 30, 60, 120, 300, 600, 1800),
)
pipeline_queue_time = Histogram(
    f"{PREFIX}_queue_time_seconds",
    "Time jobs spend in queue before processing",
    ["stage"],
    buckets=(1, 5, 10, 30, 60, 120, 300),
)

# Gauges
active_pipelines = Gauge(f"{PREFIX}_active", "Currently active pipelines", ["pipeline_type"])
stage_success_rate = Gauge(f"{PREFIX}_stage_success_rate", "Stage success rate (0-1)", ["stage"])


@dataclass
class PipelineMetricsSnapshot:
    pipeline_type: str = ""
    stage: str = ""
    active_count: int = 0
    total_started: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_retries: int = 0
    avg_duration_seconds: float = 0.0
    success_rate: float = 1.0
    timestamp: str = ""


class PipelineMetricsCollector:
    """Collects and exposes pipeline execution metrics to Prometheus."""

    def __init__(self):
        self._pipeline_times: dict[str, float] = {}
        self._stage_times: dict[str, dict[str, float]] = {}

    def record_pipeline_started(self, project_id: str, pipeline_type: str = "full") -> None:
        pipeline_started.labels(project_id=project_id, pipeline_type=pipeline_type).inc()
        active_pipelines.labels(pipeline_type=pipeline_type).inc()
        self._pipeline_times[project_id] = time.monotonic()
        logger.info("pipeline_started", project_id=project_id, pipeline_type=pipeline_type)

    def record_pipeline_completed(self, project_id: str, pipeline_type: str = "full") -> None:
        pipeline_completed.labels(project_id=project_id, pipeline_type=pipeline_type).inc()
        active_pipelines.labels(pipeline_type=pipeline_type).dec()
        if project_id in self._pipeline_times:
            duration = time.monotonic() - self._pipeline_times.pop(project_id, 0)
            pipeline_duration.labels(pipeline_type=pipeline_type).observe(duration)
        logger.info("pipeline_completed", project_id=project_id, pipeline_type=pipeline_type)

    def record_pipeline_failed(self, project_id: str, stage: str, pipeline_type: str = "full") -> None:
        pipeline_failed.labels(project_id=project_id, pipeline_type=pipeline_type, stage=stage).inc()
        active_pipelines.labels(pipeline_type=pipeline_type).dec()
        if project_id in self._pipeline_times:
            self._pipeline_times.pop(project_id, None)
        logger.warning("pipeline_failed", project_id=project_id, stage=stage, pipeline_type=pipeline_type)

    def record_stage_started(self, project_id: str, stage: str, pipeline_type: str = "full") -> None:
        if project_id not in self._stage_times:
            self._stage_times[project_id] = {}
        self._stage_times[project_id][stage] = time.monotonic()

    def record_stage_completed(self, project_id: str, stage: str, pipeline_type: str = "full") -> None:
        if project_id in self._stage_times and stage in self._stage_times[project_id]:
            duration = time.monotonic() - self._stage_times[project_id].pop(stage, 0)
            stage_duration.labels(stage=stage, pipeline_type=pipeline_type).observe(duration)

    def record_stage_retried(self, stage: str) -> None:
        pipeline_retried.labels(stage=stage).inc()

    def record_checkpoint(self, stage: str) -> None:
        pipeline_checkpoint.labels(stage=stage).inc()

    def record_resume(self, project_id: str) -> None:
        pipeline_resumed.labels(project_id=project_id).inc()

    def record_queue_time(self, stage: str, seconds: float) -> None:
        pipeline_queue_time.labels(stage=stage).observe(seconds)

    def update_stage_success_rate(self, stage: str, rate: float) -> None:
        stage_success_rate.labels(stage=stage).set(max(0.0, min(1.0, rate)))

    def get_snapshot(self) -> PipelineMetricsSnapshot:
        return PipelineMetricsSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def get_active_pipeline_count(self) -> int:
        samples = list(active_pipelines.collect())
        total = 0
        for s in samples:
            for sample in s.samples:
                total += int(sample.value)
        return total


_pipeline_metrics: PipelineMetricsCollector | None = None


def get_pipeline_metrics() -> PipelineMetricsCollector:
    global _pipeline_metrics
    if _pipeline_metrics is None:
        _pipeline_metrics = PipelineMetricsCollector()
    return _pipeline_metrics
