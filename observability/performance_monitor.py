from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from observability.logger import get_logger


@dataclass
class ProfileSample:
    operation: str
    duration_ms: float
    module: str = ""
    success: bool = True
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class ProfileSummary:
    operation: str
    call_count: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    min_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    error_count: int = 0

    def to_dict(self) -> dict[str, float | int]:
        return {
            "operation": self.operation,
            "call_count": self.call_count,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "min_duration_ms": round(self.min_duration_ms, 2),
            "max_duration_ms": round(self.max_duration_ms, 2),
            "p50_ms": round(self.p50_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
            "error_count": self.error_count,
        }


class PerformanceMonitor:
    def __init__(self, slow_threshold_ms: float = 1000.0):
        self._samples: list[ProfileSample] = []
        self._slow_threshold = slow_threshold_ms
        self._logger = get_logger(__name__)

    def record(self, operation: str, duration_ms: float, module: str = "", success: bool = True) -> None:
        sample = ProfileSample(
            operation=operation,
            duration_ms=duration_ms,
            module=module,
            success=success,
        )
        self._samples.append(sample)
        if duration_ms > self._slow_threshold:
            self._logger.warning(
                "slow_operation",
                operation=operation,
                duration_ms=round(duration_ms, 2),
                module=module,
                threshold_ms=self._slow_threshold,
            )

    @property
    def slow_threshold_ms(self) -> float:
        return self._slow_threshold

    @slow_threshold_ms.setter
    def slow_threshold_ms(self, value: float) -> None:
        self._slow_threshold = value

    def get_summary(self, operation: str | None = None) -> dict[str, Any]:
        if operation:
            samples = [s for s in self._samples if s.operation == operation]
        else:
            samples = self._samples
        if not samples:
            return {}
        by_op: dict[str, list[ProfileSample]] = defaultdict(list)
        for s in samples:
            by_op[s.operation].append(s)
        summaries = {}
        for op, recs in by_op.items():
            durations = [r.duration_ms for r in recs]
            durations.sort()
            n = len(durations)
            p50 = durations[n // 2] if n % 2 == 1 else (durations[n // 2 - 1] + durations[n // 2]) / 2.0
            summaries[op] = ProfileSummary(
                operation=op,
                call_count=n,
                total_duration_ms=sum(durations),
                avg_duration_ms=sum(durations) / n,
                min_duration_ms=durations[0],
                max_duration_ms=durations[-1],
                p50_ms=p50,
                p95_ms=durations[int(n * 0.95) - 1],
                p99_ms=durations[int(n * 0.99) - 1],
                error_count=sum(1 for r in recs if not r.success),
            )
        return {op: s.to_dict() for op, s in summaries.items()}

    def get_slow_operations(self, threshold_ms: float | None = None) -> list[dict[str, Any]]:
        threshold = threshold_ms or self._slow_threshold
        slow = [s for s in self._samples if s.duration_ms > threshold]
        return [
            {
                "operation": s.operation,
                "duration_ms": round(s.duration_ms, 2),
                "module": s.module,
                "timestamp": s.timestamp,
            }
            for s in slow[-100:]
        ]

    def get_aggregate_summary(self) -> dict[str, Any]:
        if not self._samples:
            return {}
        by_module: dict[str, int] = defaultdict(int)
        total_slow = sum(1 for s in self._samples if s.duration_ms > self._slow_threshold)
        for s in self._samples:
            by_module[s.module] += 1
        durations = [s.duration_ms for s in self._samples]
        return {
            "total_samples": len(self._samples),
            "slow_operations": total_slow,
            "slow_threshold_ms": self._slow_threshold,
            "avg_duration_ms": round(sum(durations) / len(durations), 2),
            "max_duration_ms": round(max(durations), 2),
            "by_module": dict(by_module),
        }

    def clear(self) -> None:
        self._samples.clear()
