"""Memory Optimizer — monitors and optimizes memory usage.

Tracks heap size, GC pressure, and provides memory optimization
recommendations. Detects potential memory leaks.
Target: heap < 500MB, GC pressure < 5%.
"""

from __future__ import annotations

import gc
import logging
import os
import threading
import time
from typing import Any

from performance_engineering.config import PerformanceConfig

logger = logging.getLogger(__name__)


class MemoryOptimizer:
    """Monitors and optimizes memory usage.

    Periodically checks heap size, GC statistics, and RSS.
    Provides recommendations for memory optimization.
    Detects potential memory leaks by tracking object growth.
    """

    def __init__(self, config: PerformanceConfig | None = None) -> None:
        self._config = config or PerformanceConfig.from_env()
        self._enabled = self._config.memory_track_enabled
        self._max_heap_mb = self._config.memory_max_heap_mb
        self._gc_threshold = self._config.memory_gc_threshold

        self._snapshots: list[dict[str, Any]] = []
        self._max_snapshots = 100
        self._object_counts: dict[str, int] = {}

        if self._enabled:
            gc.set_threshold(*gc.get_threshold())
            self._take_snapshot("init")

    def _take_snapshot(self, label: str = "") -> dict[str, Any]:
        """Take a memory usage snapshot.

        Args:
            label: Optional label for the snapshot.

        Returns:
            Snapshot data dict.
        """
        import tracemalloc

        # Get heap size
        try:
            import psutil
            process = psutil.Process(os.getpid())
            rss_mb = process.memory_info().rss / (1024 * 1024)
        except ImportError:
            rss_mb = 0.0

        # Get GC stats
        gc_count = gc.get_count()
        gc_stats = gc.get_stats()

        # Get object counts for common types
        obj_counts = {}
        for obj_type in ["dict", "list", "str", "tuple", "set"]:
            obj_counts[obj_type] = len(gc.get_objects() if False else [])
            # Approximate: use type count from gc
            type_objs = [
                o for o in gc.get_objects()
                if type(o).__name__ == obj_type
            ]
            obj_counts[obj_type] = len(type_objs)

        snapshot = {
            "timestamp": time.time(),
            "label": label,
            "rss_mb": round(rss_mb, 1),
            "gc_count": gc_count,
            "gc_collected": gc_stats[0].get("collected", 0) if gc_stats else 0,
            "object_counts": obj_counts,
        }

        self._snapshots.append(snapshot)
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots.pop(0)

        return snapshot

    def get_memory_usage(self) -> dict[str, Any]:
        """Get current memory usage.

        Returns:
            Dict with memory metrics.
        """
        snapshot = self._take_snapshot("check")
        return {
            "rss_mb": snapshot["rss_mb"],
            "max_heap_mb": self._max_heap_mb,
            "usage_pct": round(
                snapshot["rss_mb"] / max(self._max_heap_mb, 1) * 100, 1
            ),
            "gc_pressure": self._get_gc_pressure(),
        }

    def detect_leaks(self) -> list[str]:
        """Detect potential memory leaks.

        Compares object counts between recent snapshots.

        Returns:
            List of potential leak candidates.
        """
        if len(self._snapshots) < 2:
            return []

        recent = self._snapshots[-1]
        prev = self._snapshots[-2]
        leaks = []

        for obj_type, count in recent.get("object_counts", {}).items():
            prev_count = prev.get("object_counts", {}).get(obj_type, 0)
            if prev_count > 0 and count > prev_count * 1.5:
                leaks.append(f"{obj_type}: {prev_count} -> {count} ({((count/prev_count)-1)*100:.0f}% growth)")

        return leaks

    def optimize(self) -> dict[str, Any]:
        """Run memory optimization.

        Forces garbage collection and returns optimization results.

        Returns:
            Dict with optimization results.
        """
        before = self._take_snapshot("before_gc")

        # Force garbage collection
        gc.collect()
        gc.collect()
        gc.collect()

        after = self._take_snapshot("after_gc")

        freed_mb = before["rss_mb"] - after["rss_mb"]

        if freed_mb > 1:
            logger.info("Memory optimizer freed %.1f MB", freed_mb)

        return {
            "freed_mb": round(freed_mb, 1),
            "before_rss_mb": before["rss_mb"],
            "after_rss_mb": after["rss_mb"],
        }

    def _get_gc_pressure(self) -> float:
        """Calculate GC pressure as a percentage."""
        if not self._snapshots:
            return 0.0
        recent = self._snapshots[-1]
        gc_count = recent.get("gc_count", 0)
        # GC count is a tuple (objects in generation 0, 1, 2)
        if isinstance(gc_count, (list, tuple)):
            total = sum(gc_count)
        else:
            total = gc_count
        return round(total / max(self._gc_threshold, 1) * 100, 1)

    def get_summary(self) -> dict[str, Any]:
        """Get memory optimization summary.

        Returns:
            Dict with memory stats and recommendations.
        """
        usage = self.get_memory_usage()
        leaks = self.detect_leaks()

        return {
            "current_rss_mb": usage["rss_mb"],
            "usage_pct": usage["usage_pct"],
            "gc_pressure_pct": usage["gc_pressure"],
            "leak_candidates": leaks,
            "snapshot_count": len(self._snapshots),
        }
