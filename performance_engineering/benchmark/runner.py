"""Benchmark Runner — before/after performance comparison.

Runs benchmark scenarios and compares results against a baseline.
Generates structured reports with performance deltas.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from performance_engineering.config import PerformanceConfig
from performance_engineering.models import BenchmarkResult

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """Runs performance benchmarks and compares results.

    Supports warmup runs, sample collection, and before/after comparison.
    Detects performance regressions (>10% degradation).
    """

    def __init__(self, config: PerformanceConfig | None = None) -> None:
        self._config = config or PerformanceConfig.from_env()
        self._baselines: dict[str, dict[str, float]] = {}

    def run_scenario(
        self,
        scenario_name: str,
        fn: Callable,
        warmup: int = 0,
        samples: int = 10,
    ) -> dict[str, float]:
        """Run a benchmark scenario and collect timing samples.

        Args:
            scenario_name: Scenario name.
            fn: Function to benchmark.
            warmup: Number of warmup iterations.
            samples: Number of timed samples.

        Returns:
            Dict of metric_name -> value.
        """
        # Warmup
        for _ in range(warmup):
            fn()

        # Timed samples
        timings = []
        for _ in range(samples):
            start = time.time()
            fn()
            timings.append((time.time() - start) * 1000)

        sorted_t = sorted(timings)
        n = len(sorted_t)

        results = {
            f"{scenario_name}_avg_ms": round(sum(sorted_t) / n, 1),
            f"{scenario_name}_min_ms": round(sorted_t[0], 1),
            f"{scenario_name}_max_ms": round(sorted_t[-1], 1),
            f"{scenario_name}_p50_ms": round(sorted_t[int(n * 0.50)], 1),
            f"{scenario_name}_p95_ms": round(sorted_t[int(n * 0.95)], 1),
            f"{scenario_name}_p99_ms": round(sorted_t[int(n * 0.99)], 1),
            f"{scenario_name}_samples": n,
        }

        return results

    def compare(
        self,
        scenario_name: str,
        before_fn: Callable,
        after_fn: Callable,
        warmup: int = 5,
        samples: int = 20,
    ) -> BenchmarkResult:
        """Compare performance before and after a change.

        Args:
            scenario_name: Scenario name.
            before_fn: Function representing the "before" state.
            after_fn: Function representing the "after" state.
            warmup: Number of warmup iterations.
            samples: Number of timed samples.

        Returns:
            ``BenchmarkResult`` with comparison data.
        """
        before = self.run_scenario(
            f"{scenario_name}_before", before_fn, warmup, samples
        )
        after = self.run_scenario(
            f"{scenario_name}_after", after_fn, warmup, samples
        )

        # Calculate improvement
        before_p95 = before.get(f"{scenario_name}_before_p95_ms", 0)
        after_p95 = after.get(f"{scenario_name}_after_p95_ms", 0)
        improvement = 0.0
        regression = False
        if before_p95 > 0:
            improvement = round(
                (before_p95 - after_p95) / before_p95 * 100, 2
            )
            regression = improvement < -10  # >10% regression

        return BenchmarkResult(
            scenario_name=scenario_name,
            before=before,
            after=after,
            improvement_pct=improvement,
            regression=regression,
            metrics=list(before.keys()),
        )

    def save_baseline(
        self, name: str, results: dict[str, float]
    ) -> None:
        """Save a benchmark baseline for future comparison.

        Args:
            name: Baseline name.
            results: Benchmark results.
        """
        self._baselines[name] = dict(results)

    def compare_against_baseline(
        self, name: str, results: dict[str, float]
    ) -> BenchmarkResult | None:
        """Compare current results against a saved baseline.

        Args:
            name: Baseline name.
            results: Current benchmark results.

        Returns:
            ``BenchmarkResult`` if baseline exists, else None.
        """
        baseline = self._baselines.get(name)
        if baseline is None:
            return None

        improvement = 0.0
        regression = False
        baseline_p95 = baseline.get(f"{name}_p95_ms", 0)
        current_p95 = results.get(f"{name}_p95_ms", 0)

        if baseline_p95 > 0:
            improvement = round(
                (baseline_p95 - current_p95) / baseline_p95 * 100, 2
            )
            regression = improvement < -10

        return BenchmarkResult(
            scenario_name=name,
            before=baseline,
            after=results,
            improvement_pct=improvement,
            regression=regression,
            metrics=list(results.keys()),
        )
