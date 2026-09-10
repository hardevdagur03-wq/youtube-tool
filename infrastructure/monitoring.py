from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Any

MAX_SAMPLES = 1000


class MetricsCollector:
    """Thread-safe metrics collector with bounded memory."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._export_times: list[float] = []
        self._api_response_times: list[float] = []
        self._exports_started = 0
        self._exports_completed = 0
        self._exports_failed = 0
        self._exports_cancelled = 0
        self._api_calls = 0
        self._api_errors = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._retries = 0
        self._videos_exported = 0
        self._total_bytes_written = 0
        self._slow_requests: list[dict] = []
        self._errors_by_type: dict[str, int] = defaultdict(int)
        self._start_time = time.time()

    def _bounded_append(self, lst: list, val: float) -> None:
        lst.append(val)
        if len(lst) > MAX_SAMPLES:
            lst[:len(lst) - MAX_SAMPLES] = []

    def record_export_start(self) -> None:
        with self._lock:
            self._exports_started += 1

    def record_export_complete(self, elapsed: float, videos: int, bytes_written: int) -> None:
        with self._lock:
            self._exports_completed += 1
            self._bounded_append(self._export_times, elapsed)
            self._videos_exported += videos
            self._total_bytes_written += bytes_written

    def record_export_failed(self) -> None:
        with self._lock:
            self._exports_failed += 1

    def record_export_cancelled(self) -> None:
        with self._lock:
            self._exports_cancelled += 1

    def record_api_call(self, elapsed: float) -> None:
        with self._lock:
            self._api_calls += 1
            self._bounded_append(self._api_response_times, elapsed)

    def record_api_error(self) -> None:
        with self._lock:
            self._api_errors += 1

    def record_cache_hit(self) -> None:
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self._cache_misses += 1

    def record_retry(self) -> None:
        with self._lock:
            self._retries += 1

    def record_error(self, error_type: str) -> None:
        with self._lock:
            self._errors_by_type[error_type] += 1

    def record_slow_request(self, path: str, elapsed: float, method: str = "GET") -> None:
        with self._lock:
            self._slow_requests.append({
                "path": path, "method": method,
                "elapsed": round(elapsed, 3), "timestamp": time.time(),
            })
            if len(self._slow_requests) > 100:
                self._slow_requests = self._slow_requests[-100:]

    def get_metrics(self) -> dict[str, Any]:
        with self._lock:
            uptime = time.time() - self._start_time
            avg_export = sum(self._export_times) / len(self._export_times) if self._export_times else 0
            avg_api = sum(self._api_response_times) / len(self._api_response_times) if self._api_response_times else 0
            total = self._exports_completed + self._exports_failed
            success_rate = (self._exports_completed / total * 100) if total > 0 else 100.0
            cache_total = self._cache_hits + self._cache_misses
            cache_ratio = (self._cache_hits / cache_total * 100) if cache_total > 0 else 0
            return {
                "uptime_seconds": round(uptime),
                "uptime_human": self._format_uptime(uptime),
                "exports": {
                    "started": self._exports_started,
                    "completed": self._exports_completed,
                    "failed": self._exports_failed,
                    "cancelled": self._exports_cancelled,
                    "success_rate": round(success_rate, 1),
                },
                "performance": {
                    "avg_export_time_seconds": round(avg_export, 2),
                    "avg_api_response_seconds": round(avg_api, 3),
                    "total_videos_exported": self._videos_exported,
                    "total_bytes_written": self._total_bytes_written,
                },
                "api": {
                    "total_calls": self._api_calls,
                    "total_errors": self._api_errors,
                    "error_rate": round((self._api_errors / self._api_calls * 100), 2) if self._api_calls > 0 else 0,
                },
                "cache": {
                    "hits": self._cache_hits,
                    "misses": self._cache_misses,
                    "hit_ratio": round(cache_ratio, 1),
                },
                "retries": self._retries,
                "errors_by_type": dict(self._errors_by_type),
                "slow_requests_count": len(self._slow_requests),
                "slow_requests": self._slow_requests[-10:],
            }

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        parts = []
        if days: parts.append(f"{days}d")
        if hours: parts.append(f"{hours}h")
        if minutes: parts.append(f"{minutes}m")
        parts.append(f"{secs}s")
        return " ".join(parts)


metrics = MetricsCollector()
