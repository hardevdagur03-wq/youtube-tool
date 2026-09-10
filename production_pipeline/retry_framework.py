"""Retry Framework — classification-based retry with per-class policies.

Each error class has its own retry policy (max_retries, backoff, jitter).
Integrates with the Global Error Handler for error classification.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Callable

from production_pipeline.config import PipelineHardeningConfig
from production_pipeline.constants import ErrorClass
from production_pipeline.error_handler import classify_error

logger = logging.getLogger(__name__)

# Default retry policies per error class
DEFAULT_RETRY_POLICIES: dict[str, dict[str, Any]] = {
    ErrorClass.AI.value: {
        "max_retries": 3,
        "base_delay": 2.0,
        "max_delay": 60.0,
        "backoff_factor": 2.0,
        "jitter": 0.25,
    },
    ErrorClass.DATABASE.value: {
        "max_retries": 2,
        "base_delay": 1.0,
        "max_delay": 10.0,
        "backoff_factor": 1.5,
        "jitter": 0.10,
    },
    ErrorClass.REDIS.value: {
        "max_retries": 3,
        "base_delay": 0.5,
        "max_delay": 5.0,
        "backoff_factor": 1.0,
        "jitter": 0.10,
    },
    ErrorClass.NETWORK.value: {
        "max_retries": 3,
        "base_delay": 1.0,
        "max_delay": 30.0,
        "backoff_factor": 2.0,
        "jitter": 0.25,
    },
    ErrorClass.TIMEOUT.value: {
        "max_retries": 2,
        "base_delay": 1.0,
        "max_delay": 10.0,
        "backoff_factor": 1.0,
        "jitter": 0.0,
    },
    ErrorClass.EXTERNAL_API.value: {
        "max_retries": 2,
        "base_delay": 2.0,
        "max_delay": 30.0,
        "backoff_factor": 2.0,
        "jitter": 0.25,
    },
    ErrorClass.WORKER.value: {
        "max_retries": 1,
        "base_delay": 5.0,
        "max_delay": 30.0,
        "backoff_factor": 2.0,
        "jitter": 0.0,
    },
    ErrorClass.STORAGE.value: {
        "max_retries": 0,
        "base_delay": 0.0,
        "max_delay": 0.0,
        "backoff_factor": 1.0,
        "jitter": 0.0,
    },
    ErrorClass.VALIDATION.value: {
        "max_retries": 0,
        "base_delay": 0.0,
        "max_delay": 0.0,
        "backoff_factor": 1.0,
        "jitter": 0.0,
    },
    ErrorClass.UNKNOWN.value: {
        "max_retries": 0,
        "base_delay": 0.0,
        "max_delay": 0.0,
        "backoff_factor": 1.0,
        "jitter": 0.0,
    },
}


class RetryFramework:
    """Classification-based retry engine.

    Each error class has its own retry policy. Retry decisions are based
    on the classified error type, not the raw exception.
    """

    def __init__(self, config: PipelineHardeningConfig | None = None) -> None:
        self._config = config or PipelineHardeningConfig()
        self._policies = dict(DEFAULT_RETRY_POLICIES)
        self._retry_history: dict[str, list[dict[str, Any]]] = {}

    def should_retry(
        self,
        error: Exception,
        error_class: ErrorClass | None = None,
        attempt: int = 1,
        execution_id: str = "",
        stage_name: str = "",
    ) -> tuple[bool, float, str]:
        """Determine if an error should be retried.

        Args:
            error: The exception.
            error_class: Pre-classified error class (or None to auto-classify).
            attempt: Current attempt number (1-based).
            execution_id: Execution ID for history.
            stage_name: Stage name for history.

        Returns:
            Tuple of (should_retry, delay_seconds, reason).
        """
        if error_class is None:
            error_class, _, _ = classify_error(error)

        policy = self._policies.get(error_class.value, self._policies[ErrorClass.UNKNOWN.value])
        max_retries = policy["max_retries"]

        if attempt > max_retries:
            self._record_attempt(execution_id, stage_name, attempt, error, False,
                                  f"Max retries ({max_retries}) exceeded")
            return False, 0.0, f"Max retries ({max_retries}) exceeded for {error_class.value}"

        # Calculate delay with exponential backoff and jitter
        base_delay = policy["base_delay"]
        backoff = policy["backoff_factor"]
        max_delay = policy["max_delay"]
        jitter = policy["jitter"]

        delay = min(base_delay * (backoff ** (attempt - 1)), max_delay)
        if jitter > 0:
            delay = delay + random.uniform(-delay * jitter, delay * jitter)
        delay = max(0.1, delay)

        self._record_attempt(execution_id, stage_name, attempt, error, True,
                              f"Retrying in {delay:.1f}s (attempt {attempt}/{max_retries})")

        return True, round(delay, 2), f"{error_class.value} error: retrying"

    def execute_with_retry(
        self,
        fn: Callable[[], Any],
        execution_id: str = "",
        stage_name: str = "",
    ) -> tuple[bool, Any, str, int]:
        """Execute a function with classification-based retry.

        Args:
            fn: Function to execute.
            execution_id: Execution ID for history.
            stage_name: Stage name for history.

        Returns:
            Tuple of (success, result, error_message, attempts_made).
        """
        last_error = ""
        attempts = 0

        for attempt in range(1, 20):  # Safety limit
            attempts += 1
            try:
                result = fn()
                return True, result, "", attempts
            except Exception as exc:
                last_error = str(exc)
                should_retry, delay, reason = self.should_retry(
                    exc, attempt=attempt,
                    execution_id=execution_id, stage_name=stage_name,
                )
                if should_retry:
                    logger.warning(
                        "[%s] Stage '%s' retry %d: %s",
                        execution_id[:8] if execution_id else "?", stage_name,
                        attempt, reason,
                    )
                    time.sleep(delay)
                else:
                    logger.warning(
                        "[%s] Stage '%s' not retrying: %s",
                        execution_id[:8] if execution_id else "?", stage_name,
                        reason,
                    )
                    return False, None, last_error, attempts

        return False, None, last_error, attempts

    def get_policy(self, error_class: ErrorClass) -> dict[str, Any]:
        """Get the retry policy for an error class."""
        return dict(self._policies.get(error_class.value, self._policies[ErrorClass.UNKNOWN.value]))

    def set_policy(self, error_class: ErrorClass, policy: dict[str, Any]) -> None:
        """Override the retry policy for an error class."""
        self._policies[error_class.value] = policy

    def get_retry_history(
        self, execution_id: str, stage_name: str | None = None
    ) -> list[dict[str, Any]]:
        """Get retry history for an execution.

        Args:
            execution_id: Execution ID.
            stage_name: Optional stage filter.

        Returns:
            List of retry attempt records.
        """
        key = f"{execution_id}:{stage_name}" if stage_name else execution_id
        history = self._retry_history.get(key, [])
        if stage_name and not key.endswith(":"):
            pass
        return history

    def _record_attempt(
        self, execution_id: str, stage_name: str,
        attempt: int, error: Exception,
        will_retry: bool, reason: str,
    ) -> None:
        """Record a retry attempt in history."""
        error_class, _, _ = classify_error(error)
        record = {
            "attempt": attempt,
            "error": str(error)[:200],
            "error_class": error_class.value,
            "will_retry": will_retry,
            "reason": reason,
            "timestamp": time.time(),
        }
        key = f"{execution_id}:{stage_name}"
        if key not in self._retry_history:
            self._retry_history[key] = []
        self._retry_history[key].append(record)

    def reset_history(self) -> None:
        """Clear all retry history."""
        self._retry_history.clear()
