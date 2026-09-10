"""Pipeline Metrics — collects execution metrics for pipelines and stages.

No existing code is modified.
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Any


class PipelineMetrics:
    """Thread-safe metrics collector for pipelines."""

    def __init__(self, max_samples: int = 1000) -> None:
        self._lock = Lock()
        self._max_samples = max_samples
        self._pipeline_durations: list[float] = []
        self._stage_durations: dict[str, list[float]] = defaultdict(list)
        self._pipeline_count = 0
        self._pipeline_success = 0
        self._pipeline_failed = 0
        self._stage_retries: dict[str, int] = defaultdict(int)
        self._cache_hits = 0
        self._cache_misses = 0
        self._llm_calls = 0
        self._llm_tokens = 0
        self._api_calls = 0
        self._errors_by_type: dict[str, int] = defaultdict(int)

    def record_pipeline_complete(self, duration: float, success: bool) -> None:
        with self._lock:
            self._pipeline_count += 1
            if success:
                self._pipeline_success += 1
            else:
                self._pipeline_failed += 1
            self._pipeline_durations.append(duration)
            if len(self._pipeline_durations) > self._max_samples:
                self._pipeline_durations = self._pipeline_durations[-self._max_samples:]

    def record_stage_complete(self, stage: str, duration: float) -> None:
        with self._lock:
            self._stage_durations[stage].append(duration)
            if len(self._stage_durations[stage]) > self._max_samples:
                self._stage_durations[stage] = self._stage_durations[stage][-self._max_samples:]

    def record_retry(self, stage: str) -> None:
        with self._lock:
            self._stage_retries[stage] += 1

    def record_cache_hit(self) -> None:
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self._cache_misses += 1

    def record_llm_call(self, tokens: int = 0) -> None:
        with self._lock:
            self._llm_calls += 1
            self._llm_tokens += tokens

    def record_api_call(self) -> None:
        with self._lock:
            self._api_calls += 1

    def record_error(self, error_type: str) -> None:
        with self._lock:
            self._errors_by_type[error_type] += 1

    def get_report(self) -> dict[str, Any]:
        with self._lock:
            total = self._pipeline_success + self._pipeline_failed
            success_rate = (self._pipeline_success / total * 100) if total > 0 else 100.0
            avg_duration = (
                sum(self._pipeline_durations) / len(self._pipeline_durations)
                if self._pipeline_durations else 0
            )
            stage_avg = {}
            for stage, durations in self._stage_durations.items():
                stage_avg[stage] = round(sum(durations) / len(durations), 3) if durations else 0
            cache_total = self._cache_hits + self._cache_misses
            cache_rate = (self._cache_hits / cache_total * 100) if cache_total > 0 else 0
            return {
                "pipelines": {
                    "total": self._pipeline_count,
                    "success": self._pipeline_success,
                    "failed": self._pipeline_failed,
                    "success_rate": round(success_rate, 1),
                    "avg_duration_seconds": round(avg_duration, 2),
                },
                "stages": {
                    "avg_durations": stage_avg,
                    "retries": dict(self._stage_retries),
                },
                "cache": {
                    "hits": self._cache_hits,
                    "misses": self._cache_misses,
                    "hit_rate": round(cache_rate, 1),
                },
                "llm": {
                    "calls": self._llm_calls,
                    "tokens": self._llm_tokens,
                },
                "api_calls": self._api_calls,
                "errors_by_type": dict(self._errors_by_type),
            }
