"""Tests for retry and circuit breaker utilities."""

from __future__ import annotations

import asyncio
import time

import pytest

from infrastructure.retry import (
    BackoffStrategy,
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitBreakerState,
    with_retry,
)


class TestWithRetry:
    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        call_count = 0

        @with_retry(max_retries=3)
        async def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await succeed()
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure_then_succeed(self):
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        async def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("fail")
            return "ok"

        result = await fail_twice()
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhaust_retries(self):
        call_count = 0

        @with_retry(max_retries=2, base_delay=0.01)
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("always fail")

        with pytest.raises(ConnectionError):
            await always_fail()
        assert call_count == 3  # original + 2 retries

    @pytest.mark.asyncio
    async def test_only_retries_specified_exceptions(self):
        @with_retry(max_retries=2, base_delay=0.01, retryable_exceptions=(ConnectionError,))
        async def raise_value_error():
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            await raise_value_error()

    def test_sync_function(self):
        call_count = 0

        @with_retry(max_retries=2, base_delay=0.01)
        def sync_fn():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("fail")
            return "ok"

        result = sync_fn()
        assert result == "ok"
        assert call_count == 2

    def test_on_retry_callback(self):
        callback_calls = []

        @with_retry(max_retries=2, base_delay=0.01, on_retry=lambda e, attempt, delay: callback_calls.append((attempt, delay)))
        def failing():
            raise ConnectionError("fail")

        with pytest.raises(ConnectionError):
            failing()

        assert len(callback_calls) == 2
        assert callback_calls[0][0] == 1
        assert callback_calls[1][0] == 2


class TestBackoffStrategy:
    def test_exponential_backoff(self):
        from infrastructure.retry import _compute_delay

        d1 = _compute_delay(0, 1.0, 60.0, BackoffStrategy.EXPONENTIAL, jitter=False)
        d2 = _compute_delay(1, 1.0, 60.0, BackoffStrategy.EXPONENTIAL, jitter=False)
        d3 = _compute_delay(2, 1.0, 60.0, BackoffStrategy.EXPONENTIAL, jitter=False)

        assert d1 == 1.0
        assert d2 == 2.0
        assert d3 == 4.0

    def test_linear_backoff(self):
        from infrastructure.retry import _compute_delay

        d1 = _compute_delay(0, 1.0, 60.0, BackoffStrategy.LINEAR, jitter=False)
        d2 = _compute_delay(1, 1.0, 60.0, BackoffStrategy.LINEAR, jitter=False)
        d3 = _compute_delay(4, 1.0, 60.0, BackoffStrategy.LINEAR, jitter=False)

        assert d1 == 1.0
        assert d2 == 2.0
        assert d3 == 5.0

    def test_constant_backoff(self):
        from infrastructure.retry import _compute_delay

        d1 = _compute_delay(0, 2.0, 60.0, BackoffStrategy.CONSTANT, jitter=False)
        d2 = _compute_delay(5, 2.0, 60.0, BackoffStrategy.CONSTANT, jitter=False)

        assert d1 == 2.0
        assert d2 == 2.0

    def test_max_delay_capped(self):
        from infrastructure.retry import _compute_delay

        d = _compute_delay(10, 1.0, 30.0, BackoffStrategy.EXPONENTIAL, jitter=False)
        assert d <= 30.0

    def test_jitter_adds_variation(self):
        from infrastructure.retry import _compute_delay

        delays = []
        for _ in range(50):
            d = _compute_delay(0, 1.0, 60.0, BackoffStrategy.EXPONENTIAL, jitter=True)
            delays.append(d)

        assert 0.5 <= min(delays) <= 1.0


class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.allow_request() is True

    def test_opens_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=0.01)

        assert cb.allow_request() is True
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.allow_request() is False

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.05)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.allow_request() is False

        time.sleep(0.06)
        assert cb.allow_request() is True
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_half_open_success_closes(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.05)

        cb.record_failure()
        cb.record_failure()
        time.sleep(0.06)

        assert cb.allow_request() is True
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.05)

        cb.record_failure()
        cb.record_failure()
        time.sleep(0.06)

        assert cb.allow_request() is True
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

    def test_circuit_breaker_open_error(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=999)
        cb.record_failure()

        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            if not cb.allow_request():
                raise CircuitBreakerOpenError(cb.name)

        assert "test" in str(exc_info.value)
        assert exc_info.value.breaker_name == "test"

    def test_decorator_sync(self):
        cb = CircuitBreaker("decorator_test", failure_threshold=2, recovery_timeout=0.05)

        @cb
        def failing_fn():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            failing_fn()

        assert cb.failure_count == 1

    def test_half_open_limits_calls(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.05, half_open_max_calls=1)

        cb.record_failure()
        cb.record_failure()
        time.sleep(0.06)

        assert cb.allow_request() is True
        assert cb.allow_request() is False
