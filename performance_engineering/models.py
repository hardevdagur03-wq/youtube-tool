"""Performance metric models and data structures."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class StageTiming(BaseModel):
    """Timing data for a single pipeline stage."""
    stage_name: str = ""
    duration_ms: float = 0.0
    queue_time_ms: float = 0.0
    provider_latency_ms: float = 0.0
    processing_time_ms: float = 0.0
    cache_hit: bool = False
    retry_count: int = 0
    error: str = ""
    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class PipelineTiming(BaseModel):
    """Timing data for a full pipeline execution."""
    pipeline_id: str = ""
    total_duration_ms: float = 0.0
    stage_timings: list[StageTiming] = Field(default_factory=list)
    parallel_groups: int = 0
    cache_hit_count: int = 0
    cache_miss_count: int = 0
    ai_call_count: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    completed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class CacheStats(BaseModel):
    """Per-cache statistics."""
    cache_name: str = ""
    hits: int = 0
    misses: int = 0
    hit_rate: float = 0.0
    size: int = 0
    memory_bytes: int = 0
    avg_lookup_ms: float = 0.0
    avg_store_ms: float = 0.0


class LatencyPercentiles(BaseModel):
    """Latency distribution."""
    p50_ms: float = 0.0
    p90_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    avg_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    sample_count: int = 0


class ThroughputMetric(BaseModel):
    """Throughput measurement."""
    metric_name: str = ""
    value: float = 0.0
    unit: str = "ops/sec"
    window_seconds: int = 60
    sampled_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class MemorySnapshot(BaseModel):
    """Memory usage snapshot."""
    heap_mb: float = 0.0
    rss_mb: float = 0.0
    gc_count: int = 0
    gc_time_ms: float = 0.0
    object_count: int = 0
    leak_candidates: list[str] = Field(default_factory=list)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class BenchmarkResult(BaseModel):
    """Benchmark comparison result."""
    scenario_name: str = ""
    before: dict[str, float] = Field(default_factory=dict)
    after: dict[str, float] = Field(default_factory=dict)
    improvement_pct: float = 0.0
    regression: bool = False
    metrics: list[str] = Field(default_factory=list)
    ran_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
