"""Batch AI Processor — groups independent AI tasks into single LLM calls.

Reduces provider calls and token usage by batching independent AI tasks
into combined prompts. Supports graceful fallback to individual calls.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable

from performance_engineering.config import PerformanceConfig

logger = logging.getLogger(__name__)


class BatchAIProcessor:
    """Groups independent AI tasks into batched LLM calls.

    Batches:
    - Entity extraction + keyword analysis + content classification
    - SEO analysis + readability scoring + grammar checking
    - Multiple section generations

    Falls back to individual calls if batching fails.
    """

    def __init__(self, config: PerformanceConfig | None = None) -> None:
        self._config = config or PerformanceConfig.from_env()
        self._enabled = self._config.batch_ai_enabled
        self._total_batches = 0
        self._total_tokens_saved = 0
        self._batch_fallbacks = 0

    async def batch_execute(
        self,
        tasks: list[dict[str, Any]],
        batch_fn: Callable,
        fallback_fn: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Execute multiple AI tasks, optionally batched.

        Args:
            tasks: List of task dicts with 'name' and 'input' keys.
            batch_fn: Async callable that takes list of inputs, returns list of outputs.
            fallback_fn: Optional async callable for individual task execution.

        Returns:
            List of result dicts with 'name' and 'output' keys.
        """
        if not self._enabled or len(tasks) <= 1:
            return await self._execute_individual(tasks, fallback_fn or batch_fn)

        try:
            start = time.time()
            inputs = [t.get("input", "") for t in tasks]
            batch_result = await batch_fn(inputs)
            elapsed = (time.time() - start) * 1000

            self._total_batches += 1
            tokens_saved = self._estimate_tokens_saved(inputs, batch_result)
            self._total_tokens_saved += tokens_saved

            logger.info(
                "Batch AI: %d tasks in %.0fms (saved ~%d tokens)",
                len(tasks), elapsed, tokens_saved,
            )

            return [
                {"name": tasks[i].get("name", f"task_{i}"), "output": batch_result[i]}
                for i in range(min(len(tasks), len(batch_result)))
            ]

        except Exception as exc:
            logger.warning("Batch AI failed (%s), falling back to individual", exc)
            self._batch_fallbacks += 1
            return await self._execute_individual(tasks, fallback_fn or batch_fn)

    async def _execute_individual(
        self,
        tasks: list[dict[str, Any]],
        fn: Callable,
    ) -> list[dict[str, Any]]:
        """Execute tasks individually as fallback."""
        results = []
        for task in tasks:
            try:
                name = task.get("name", "unknown")
                inp = task.get("input", "")
                output = await fn([inp])
                results.append({
                    "name": name,
                    "output": output[0] if isinstance(output, list) else output,
                })
            except Exception as exc:
                results.append({
                    "name": task.get("name", "unknown"),
                    "output": {"error": str(exc)},
                })
        return results

    def _estimate_tokens_saved(
        self, inputs: list[str], outputs: Any,
    ) -> int:
        """Estimate tokens saved by batching vs individual calls."""
        total_chars = sum(len(inp) for inp in inputs)
        output_chars = len(str(outputs))
        shared_overhead = 100  # Approximate shared prompt overhead
        return max(0, (total_chars + shared_overhead) // 4 - shared_overhead // 4)

    def get_stats(self) -> dict[str, Any]:
        """Get batch AI statistics."""
        return {
            "total_batches": self._total_batches,
            "total_tokens_saved": self._total_tokens_saved,
            "batch_fallbacks": self._batch_fallbacks,
            "enabled": self._enabled,
        }

    def reset_stats(self) -> None:
        """Reset batch statistics."""
        self._total_batches = 0
        self._total_tokens_saved = 0
        self._batch_fallbacks = 0
