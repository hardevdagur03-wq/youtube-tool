"""Retry Manager — configurable retry logic with exponential backoff, jitter, and history."""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from typing import Any

from background_processing.config import BackgroundProcessingConfig
from background_processing.models import JobModel, RetryAttempt

logger = logging.getLogger(__name__)


class RetryDecision:
    """Represents a decision about whether and how to retry a failed job."""

    def __init__(
        self,
        should_retry: bool,
        delay: int = 0,
        reason: str = "",
        send_to_dead_letter: bool = False,
    ) -> None:
        self.should_retry = should_retry
        self.delay = delay
        self.reason = reason
        self.send_to_dead_letter = send_to_dead_letter


# Errors that should NEVER be retried (non-recoverable)
NON_RECOVERABLE_ERRORS = (
    "Invalid payload",
    "ValidationError",
    "JobNotFound",
    "ProjectNotFound",
    "AuthorizationError",
    "AuthenticationError",
    "PermissionDenied",
    "InvalidArgument",
    "BadRequest",
    "UnsupportedJobType",
)


class RetryManager:
    """Decides when and how to retry failed jobs.

    Supports:
    - Exponential backoff: delay * 2^attempt
    - Linear retry: constant delay between attempts
    - Jitter: randomize delay to avoid thundering herd
    - Max retry cap: never exceed backoff_max
    - Non-recoverable error detection
    - Retry history tracking
    """

    def __init__(
        self,
        config: BackgroundProcessingConfig | None = None,
    ) -> None:
        self._config = config or BackgroundProcessingConfig.from_env()

    def should_retry(
        self,
        job: JobModel,
        error: str = "",
    ) -> RetryDecision:
        """Evaluate whether a job should be retried.

        Returns a RetryDecision with the delay and whether to send to DLQ.
        """
        attempts = (job.attempts or 0) + 1
        max_retries = job.max_retries if job.max_retries is not None else self._config.default_retry_max

        # Never retry non-recoverable errors
        if self._is_non_recoverable(error):
            return RetryDecision(
                should_retry=False,
                reason=f"Non-recoverable error: {error[:100]}",
                send_to_dead_letter=True,
            )

        # Check if we've exceeded max retries
        if attempts > max_retries:
            return RetryDecision(
                should_retry=False,
                reason=f"Exceeded max retries ({max_retries})",
                send_to_dead_letter=True,
            )

        delay = self._compute_delay(attempts)
        return RetryDecision(
            should_retry=True,
            delay=delay,
            reason=f"Retry attempt {attempts}/{max_retries} in {delay}s",
        )

    def _compute_delay(self, attempt: int) -> int:
        """Compute retry delay using exponential backoff with jitter."""
        cfg = self._config
        base_delay = cfg.default_retry_delay

        if cfg.default_retry_backoff:
            delay = base_delay * (2 ** (attempt - 1))
            delay = min(delay, cfg.default_retry_backoff_max)
        else:
            delay = base_delay

        if cfg.retry_jitter:
            delay = delay * (0.5 + random.random() * 0.5)

        return int(delay)

    def build_retry_history(
        self,
        job: JobModel,
        error: str = "",
        traceback: str = "",
    ) -> list[dict[str, Any]]:
        """Append a retry attempt to the job's retry history."""
        history = list(job.retry_history or [])
        attempt = RetryAttempt(
            attempt=(job.attempts or 0) + 1,
            scheduled_at=datetime.now(timezone.utc).isoformat(),
            error=error[:500] if error else "",
            traceback=traceback[:2000] if traceback else "",
        )
        history.append(attempt.model_dump())
        return history

    def _is_non_recoverable(self, error: str) -> bool:
        """Check if the error is non-recoverable."""
        if not error:
            return False
        return any(nr in error for nr in NON_RECOVERABLE_ERRORS)

    def estimate_retry_delay(self, job: JobModel) -> int:
        """Estimate when the next retry would fire (for display purposes)."""
        attempts = (job.attempts or 0) + 1
        return self._compute_delay(attempts)
