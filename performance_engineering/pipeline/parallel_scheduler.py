"""Parallel Scheduler — DAG-based parallel stage execution.

Runs independent pipeline stages concurrently using asyncio.gather.
Analyzes the execution graph to identify parallel-executable stages.

Parallel groups based on dependency analysis:
  Level 0: [metadata]
  Level 1: [transcript]
  Level 2: [analysis]
  Level 3: [knowledge_graph, seo]               ← PARALLEL
  Level 4: [outline]
  Level 5: [sections]
  Level 6: [review, export]                      ← PARALLEL
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable

from performance_engineering.config import PerformanceConfig

logger = logging.getLogger(__name__)

# Default stage dependency graph (mirrors orchestrator/dependency_resolver.py)
_STAGE_DEPENDENCIES: dict[str, list[str]] = {
    "metadata": [],
    "transcript": ["metadata"],
    "analysis": ["transcript"],
    "knowledge_graph": ["analysis"],
    "seo": ["analysis"],
    "seo_intelligence": ["knowledge_graph"],
    "outline": ["knowledge_graph", "seo_intelligence"],
    "sections": ["outline"],
    "review": ["sections"],
    "export": ["sections"],
    "publishing": ["export"],
}


class ParallelScheduler:
    """DAG-based parallel stage scheduler.

    Analyzes stage dependencies to identify parallel-executable groups,
    then runs groups sequentially with concurrent execution within each group.
    """

    def __init__(self, config: PerformanceConfig | None = None) -> None:
        self._config = config or PerformanceConfig.from_env()
        self._dependencies = dict(_STAGE_DEPENDENCIES)

    def compute_parallel_groups(
        self, stages: list[str] | None = None,
    ) -> list[list[str]]:
        """Compute parallel execution groups from stage dependencies.

        Uses a topological breadth-first approach: stages at the same
        "level" (all dependencies satisfied) can run in parallel.

        Args:
            stages: List of stage names to schedule (defaults to all).

        Returns:
            List of lists, where each inner list contains stage names
            that can execute in parallel.
        """
        stages = stages or list(self._dependencies.keys())
        target_set = set(stages)

        # Build in-degree count for topological sort
        in_degree: dict[str, int] = {}
        for stage in stages:
            deps = [d for d in self._dependencies.get(stage, []) if d in target_set]
            in_degree[stage] = len(deps)

        groups: list[list[str]] = []
        completed: set[str] = set()

        while len(completed) < len(stages):
            # Find stages whose dependencies are all completed
            ready = [
                s for s in stages
                if s not in completed and in_degree.get(s, 0) == 0
            ]
            if not ready:
                # Circular dependency or missing dependency — add remaining
                remaining = [s for s in stages if s not in completed]
                if remaining:
                    groups.append(remaining)
                break

            groups.append(ready)
            for stage in ready:
                completed.add(stage)
                # Reduce in-degree for dependents
                for s, deps in self._dependencies.items():
                    if s in target_set and stage in deps:
                        in_degree[s] = max(0, in_degree.get(s, 1) - 1)

        return groups

    async def execute_group(
        self,
        stages: list[tuple[str, Callable]],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a group of stages in parallel.

        Args:
            stages: List of (stage_name, async_callable) tuples.
            context: Shared pipeline context.

        Returns:
            Updated context with stage outputs.
        """
        if not stages:
            return context

        async def run_single_stage(stage_name: str, func: Callable) -> tuple[str, Any]:
            start = time.time()
            try:
                result = await func(context)
                elapsed = (time.time() - start) * 1000
                logger.info(
                    "Stage '%s' completed in %.0fms (parallel group)",
                    stage_name, elapsed,
                )
                return stage_name, result
            except Exception as exc:
                elapsed = (time.time() - start) * 1000
                logger.error(
                    "Stage '%s' FAILED in %.0fms (parallel group): %s",
                    stage_name, elapsed, exc,
                )
                return stage_name, {"error": str(exc)}

        tasks = [
            run_single_stage(name, func) for name, func in stages
        ]
        results = await asyncio.gather(*tasks)

        for stage_name, result in results:
            context[stage_name] = result

        return context

    async def run_schedule(
        self,
        stage_executors: dict[str, Callable],
        initial_context: dict[str, Any] | None = None,
        stages: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run the full stage schedule with parallel execution.

        Args:
            stage_executors: Dict of stage_name -> async callable.
            initial_context: Initial pipeline context.
            stages: List of stages to run (defaults to all).

        Returns:
            Final pipeline context with all stage outputs.
        """
        context = dict(initial_context or {})
        stages = stages or list(stage_executors.keys())
        groups = self.compute_parallel_groups(stages)

        total_groups = len(groups)
        total_stages = sum(len(g) for g in groups)

        logger.info(
            "Parallel schedule: %d stages in %d groups (%.1fx speedup potential)",
            total_stages, total_groups,
            total_stages / max(total_groups, 1),
        )

        for group_idx, group in enumerate(groups):
            # Create list of (name, func) for stages in this group
            available = [
                (name, stage_executors[name])
                for name in group
                if name in stage_executors
            ]

            if not available:
                continue

            await self.execute_group(available, context)

        return context

    def estimate_speedup(
        self, stage_durations: dict[str, float],
    ) -> dict[str, Any]:
        """Estimate speedup from parallel execution.

        Args:
            stage_durations: Dict of stage_name -> duration_ms.

        Returns:
            Dict with sequential/parallel time estimates and speedup ratio.
        """
        stages = list(stage_durations.keys())
        groups = self.compute_parallel_groups(stages)

        sequential_time = sum(stage_durations.get(s, 0) for s in stages)
        parallel_time = sum(
            max(stage_durations.get(s, 0) for s in group)
            for group in groups
            if group
        )

        return {
            "sequential_time_ms": round(sequential_time, 1),
            "parallel_time_ms": round(parallel_time, 1),
            "speedup_ratio": round(
                sequential_time / max(parallel_time, 1), 2
            ),
            "groups": len(groups),
            "stages": len(stages),
        }
