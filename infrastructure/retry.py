"""Retry utilities with exponential backoff, jitter, and circuit breaker."""

from __future__ import annotations

import asyncio
import functools
import logging
import random
import time
from enum import Enum
from typing import Any, Callable, TypeVar

logger = logging.getLogger("infrastructure.retry")

T = TypeVar("T")

F = Callable[..., T]


class BackoffStrategy(str, Enum):
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    CONSTANT = "constant"


DEFAULT_RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    jitter: bool = True,
    retryable_exceptions: tuple = DEFAULT_RETRYABLE_EXCEPTIONS,
    on_retry: Callable[[Exception, int, float], None] | None = None,
) -> Callable[[F], F]:
    """Decorator that retries a callable with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay in seconds.
        backoff: Backoff strategy.
        jitter: Add random jitter to delay.
        retryable_exceptions: Tuple of exception types that trigger retry.
        on_retry: Optional callback(retry_count: int, delay: float).
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        delay = _compute_delay(attempt, base_delay, max_delay, backoff, jitter)
                        if on_retry:
                            on_retry(exc, attempt + 1, delay)
                        logger.warning(
                            "Retry %d/%d for %s after %.2fs: %s",
                            attempt + 1, max_retries, func.__name__, delay, exc,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "All %d retries exhausted for %s: %s",
                            max_retries, func.__name__, exc,
                        )
            raise last_exc  # type: ignore[misc]

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        delay = _compute_delay(attempt, base_delay, max_delay, backoff, jitter)
                        if on_retry:
                            on_retry(exc, attempt + 1, delay)
                        logger.warning(
                            "Retry %d/%d for %s after %.2fs: %s",
                            attempt + 1, max_retries, func.__name__, delay, exc,
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "All %d retries exhausted for %s: %s",
                            max_retries, func.__name__, exc,
                        )
            raise last_exc  # type: ignore[misc]

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator  # type: ignore[return-value]


def _compute_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    strategy: BackoffStrategy,
    jitter: bool,
) -> float:
    if strategy == BackoffStrategy.CONSTANT:
        delay = base_delay
    elif strategy == BackoffStrategy.LINEAR:
        delay = base_delay * (attempt + 1)
    else:
        delay = base_delay * (2 ** attempt)
    delay = min(delay, max_delay)
    if jitter:
        delay *= 0.5 + random.random() * 0.5
    return delay


class CircuitBreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """Raised when a circuit breaker is open and rejects a request."""

    def __init__(self, name: str) -> None:
        self.breaker_name = name
        super().__init__(f"Circuit breaker '{name}' is open")


class CircuitBreaker:
    """Circuit breaker to prevent repeated calls to failing services."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float = 0.0
        self.half_open_calls = 0

    def record_success(self) -> None:
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.info("Circuit breaker %s: half-open -> closed (success)", self.name)
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.half_open_calls = 0

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.warning("Circuit breaker %s: half-open -> open (failure)", self.name)
            self.state = CircuitBreakerState.OPEN
        elif self.failure_count >= self.failure_threshold:
            logger.warning(
                "Circuit breaker %s: closed -> open (%d failures)",
                self.name, self.failure_count,
            )
            self.state = CircuitBreakerState.OPEN

    def allow_request(self) -> bool:
        now = time.time()
        if self.state == CircuitBreakerState.CLOSED:
            return True
        if self.state == CircuitBreakerState.OPEN:
            if now - self.last_failure_time >= self.recovery_timeout:
                logger.info("Circuit breaker %s: open -> half-open (timeout expired)", self.name)
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 1
                return True
            return False
        if self.state == CircuitBreakerState.HALF_OPEN:
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False
        return True

    def __call__(self, func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not self.allow_request():
                raise CircuitBreakerOpenError(self.name)
            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except Exception:
                self.record_failure()
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not self.allow_request():
                raise CircuitBreakerOpenError(self.name)
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception:
                self.record_failure()
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]
