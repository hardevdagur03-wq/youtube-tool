"""Retry Manager — production-grade retry with exponential backoff.

No existing code is modified.
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 2.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    retryable_errors: tuple[str, ...] = (
        "timeout", "quota", "rate_limit", "network",
        "500", "502", "503", "504", "service_unavailable",
    )


class RetryManager:
    """Manages retry logic for pipeline stages."""

    def __init__(self, policy: RetryPolicy | None = None) -> None:
        self._policy = policy or RetryPolicy()
        self._history: dict[str, list[dict]] = {}

    async def execute_with_retry(
        self,
        stage_name: str,
        fn: Any,
        *args: Any,
        **kwargs: Any,
    ) -> tuple[bool, Any, str, int]:
        """Execute a function with retry logic.

        Returns: (success, result, error_message, retry_count)
        """
        last_error = ""
        retry_count = 0

        for attempt in range(self._policy.max_retries + 1):
            try:
                result = await fn(*args, **kwargs)
                self._record_attempt(stage_name, attempt, True)
                return True, result, "", retry_count
            except Exception as exc:
                last_error = str(exc)
                retry_count = attempt + 1
                self._record_attempt(stage_name, attempt, False, str(exc))

                if not self._should_retry(stage_name, exc, attempt):
                    break

                delay = self._compute_delay(attempt)
                logger.warning(
                    "Stage '%s' attempt %d/%d failed: %s. Retrying in %.1fs...",
                    stage_name, attempt + 1, self._policy.max_retries + 1,
                    exc, delay,
                )
                await asyncio.sleep(delay)

        logger.error(
            "Stage '%s' failed after %d retries: %s",
            stage_name, retry_count, last_error,
        )
        return False, None, last_error, retry_count

    def _should_retry(self, stage: str, exc: Exception, attempt: int) -> bool:
        if attempt >= self._policy.max_retries:
            return False
        error_str = str(exc).lower()
        for retryable in self._policy.retryable_errors:
            if retryable in error_str:
                return True
        return False

    def _compute_delay(self, attempt: int) -> float:
        delay = self._policy.base_delay * (self._policy.backoff_multiplier ** attempt)
        delay = min(delay, self._policy.max_delay)
        if self._policy.jitter:
            delay *= 0.5 + random.random() * 0.5
        return delay

    def _record_attempt(self, stage: str, attempt: int, success: bool, error: str = "") -> None:
        if stage not in self._history:
            self._history[stage] = []
        self._history[stage].append({
            "attempt": attempt + 1,
            "success": success,
            "error": error,
        })

    def get_retry_history(self, stage: str) -> list[dict]:
        return self._history.get(stage, [])

    def get_all_history(self) -> dict[str, list[dict]]:
        return dict(self._history)

    def clear_history(self) -> None:
        self._history.clear()
