"""Retry Engine — exponential backoff with jitter and per-provider policies.

Supports transient error retry, 429 retry (with Retry-After), 5xx retry,
network retry, timeout retry, and configurable retry budgets.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Callable

from transcript_reliability.config import TranscriptReliabilityConfig
from transcript_reliability.constants import RetryAction
from transcript_reliability.exceptions import (
    ProviderAuthError,
    ProviderQuotaError,
    ProviderTimeoutError,
    RetryBudgetExhaustedError,
)
from transcript_reliability.models import RetryAttempt, RetryDecision, RetryPolicy

logger = logging.getLogger(__name__)

# Error types that are NOT retryable (non-recoverable)
_NON_RETRYABLE_ERRORS = (
    ProviderAuthError,
    ValueError,
    TypeError,
    KeyError,
    ImportError,
)

# Keywords in error messages that indicate non-recoverable errors
_NON_RECOVERABLE_KEYWORDS = [
    "invalid video id",
    "video unavailable",
    "video not found",
    "deleted video",
    "private video",
    "age restricted",
    "invalid api key",
    "authentication failed",
    "unauthorized",
    "forbidden",
    "not found",
    "invalid request",
]


def _is_recoverable(error: Exception) -> bool:
    """Determine if an error is recoverable (retryable)."""
    if isinstance(error, _NON_RETRYABLE_ERRORS):
        return False
    msg = str(error).lower()
    for keyword in _NON_RECOVERABLE_KEYWORDS:
        if keyword in msg:
            return False
    return True


class RetryEngine:
    """Configurable retry engine with exponential backoff and jitter.

    Usage::

        engine = RetryEngine()
        decision = engine.decide(attempt=1, error=exc, provider_id="youtube_manual")
        if decision.action == RetryAction.RETRY:
            time.sleep(decision.delay_seconds)
            # retry
        elif decision.action == RetryAction.FAILOVER:
            # try next provider
    """

    def __init__(self, config: TranscriptReliabilityConfig | None = None) -> None:
        self._config = config or TranscriptReliabilityConfig()
        self._attempts: dict[str, list[RetryAttempt]] = {}
        self._budget_used: dict[str, int] = {}

    def decide(
        self,
        attempt: int,
        error: Exception,
        provider_id: str,
        policy: RetryPolicy | None = None,
        retry_after_header: str | None = None,
    ) -> RetryDecision:
        """Determine whether to retry, failover, or abort.

        Args:
            attempt: Current attempt number (1-based).
            error: The exception that occurred.
            provider_id: The provider that failed.
            policy: Retry policy for this provider.
            retry_after_header: Value of Retry-After header if present.

        Returns:
            ``RetryDecision`` with action and delay.
        """
        policy = policy or RetryPolicy(
            max_retries=self._config.retry_max_retries,
            base_delay=self._config.retry_base_delay,
            max_delay=self._config.retry_max_delay,
            backoff_factor=self._config.retry_backoff_factor,
            jitter=self._config.retry_jitter,
        )

        # Check retry budget
        budget_key = provider_id
        used = self._budget_used.get(budget_key, 0)
        if used >= policy.retry_budget:
            return RetryDecision(
                action=RetryAction.ABORT,
                reason=f"Retry budget exhausted ({used}/{policy.retry_budget})",
                attempt=attempt,
            )

        # Check if error is recoverable
        if not _is_recoverable(error):
            error_msg = str(error).lower()
            if any(kw in error_msg for kw in _NON_RECOVERABLE_KEYWORDS):
                return RetryDecision(
                    action=RetryAction.FAILOVER,
                    reason=f"Non-recoverable error: {error}",
                    attempt=attempt,
                )
            return RetryDecision(
                action=RetryAction.ABORT,
                reason=f"Non-recoverable error type: {type(error).__name__}",
                attempt=attempt,
            )

        # Check max retries
        if attempt >= policy.max_retries:
            return RetryDecision(
                action=RetryAction.FAILOVER,
                reason=f"Max retries ({policy.max_retries}) exceeded",
                attempt=attempt,
            )

        # Calculate delay with exponential backoff and jitter
        delay = min(
            policy.base_delay * (policy.backoff_factor ** (attempt - 1)),
            policy.max_delay,
        )

        # Apply Retry-After header if present
        if retry_after_header:
            try:
                retry_after = float(retry_after_header)
                delay = max(delay, retry_after)
            except (ValueError, TypeError):
                pass

        # Apply jitter
        jitter = delay * policy.jitter
        delay = delay + random.uniform(-jitter, jitter)
        delay = max(0.1, delay)

        self._budget_used[budget_key] = used + 1

        # Record attempt
        if provider_id not in self._attempts:
            self._attempts[provider_id] = []
        self._attempts[provider_id].append(RetryAttempt(
            attempt_number=attempt,
            provider_id=provider_id,
            delay_seconds=round(delay, 2),
            error=str(error),
            timestamp=time.time(),
        ))

        return RetryDecision(
            action=RetryAction.RETRY,
            delay_seconds=round(delay, 2),
            attempt=attempt,
            reason=f"Retry {attempt}/{policy.max_retries} in {delay:.1f}s",
        )

    def execute_with_retry(
        self,
        fn: Callable[[], Any],
        provider_id: str,
        policy: RetryPolicy | None = None,
    ) -> tuple[bool, Any, str, int]:
        """Execute a function with retry logic.

        Args:
            fn: The function to execute.
            provider_id: Provider ID for tracking.
            policy: Optional retry policy override.

        Returns:
            Tuple of (success, result, error_message, attempts_made).
        """
        policy = policy or RetryPolicy(
            max_retries=self._config.retry_max_retries,
            base_delay=self._config.retry_base_delay,
            max_delay=self._config.retry_max_delay,
            backoff_factor=self._config.retry_backoff_factor,
            jitter=self._config.retry_jitter,
        )

        last_error = ""
        attempts = 0

        for attempt in range(1, policy.max_retries + 2):  # +1 for initial attempt
            attempts += 1
            try:
                result = fn()
                return True, result, "", attempts
            except Exception as exc:
                last_error = str(exc)
                decision = self.decide(attempt, exc, provider_id, policy)
                if decision.action == RetryAction.RETRY:
                    logger.warning(
                        "[%s] %s: %s",
                        provider_id, decision.reason, last_error,
                    )
                    time.sleep(decision.delay_seconds)
                elif decision.action == RetryAction.FAILOVER:
                    logger.warning(
                        "[%s] Failover after %d attempts: %s",
                        provider_id, attempts, last_error,
                    )
                    return False, None, last_error, attempts
                else:
                    logger.error(
                        "[%s] Abort after %d attempts: %s",
                        provider_id, attempts, last_error,
                    )
                    return False, None, last_error, attempts

        return False, None, last_error, attempts

    def get_attempts(self, provider_id: str) -> list[RetryAttempt]:
        """Get retry history for a provider."""
        return self._attempts.get(provider_id, [])

    def reset_budget(self, provider_id: str) -> None:
        """Reset retry budget for a provider."""
        self._budget_used.pop(provider_id, None)
        self._attempts.pop(provider_id, None)

    def reset_all(self) -> None:
        """Reset all retry state."""
        self._attempts.clear()
        self._budget_used.clear()
