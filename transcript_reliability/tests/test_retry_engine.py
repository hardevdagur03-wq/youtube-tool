"""Tests for the Retry Engine."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from transcript_reliability.retry_engine import RetryEngine, _is_recoverable
from transcript_reliability.constants import RetryAction
from transcript_reliability.exceptions import ProviderAuthError, ProviderQuotaError
from transcript_reliability.models import RetryPolicy


class TestIsRecoverable:
    def test_auth_error_not_recoverable(self):
        assert _is_recoverable(ProviderAuthError("API key invalid")) == False

    def test_value_error_not_recoverable(self):
        assert _is_recoverable(ValueError("invalid video id")) == False

    def test_timeout_is_recoverable(self):
        assert _is_recoverable(TimeoutError("connection timed out")) == True

    def test_non_recoverable_keywords(self):
        assert _is_recoverable(Exception("Video not found")) == False
        assert _is_recoverable(Exception("invalid api key")) == False
        assert _is_recoverable(Exception("private video")) == False
        assert _is_recoverable(Exception("Not Found")) == False

    def test_generic_error_recoverable(self):
        assert _is_recoverable(Exception("Something went wrong")) == True


class TestRetryEngine:
    def test_initial_retry(self):
        engine = RetryEngine()
        decision = engine.decide(1, Exception("timeout"), "test_provider")
        assert decision.action == RetryAction.RETRY
        assert decision.delay_seconds > 0
        assert decision.attempt == 1

    def test_max_retries_exceeded(self):
        engine = RetryEngine()
        decision = engine.decide(3, Exception("timeout"), "test_provider",
                                  policy=RetryPolicy(max_retries=3))
        assert decision.action == RetryAction.FAILOVER
        assert "Max retries" in decision.reason

    def test_non_recoverable_failover(self):
        engine = RetryEngine()
        decision = engine.decide(1, ValueError("invalid video id"), "test_provider")
        assert decision.action == RetryAction.FAILOVER

    def test_non_recoverable_keyword_failover(self):
        engine = RetryEngine()
        decision = engine.decide(1, Exception("Video not found"), "test_provider")
        assert decision.action == RetryAction.FAILOVER

    def test_retry_budget_exhausted(self):
        engine = RetryEngine()
        policy = RetryPolicy(max_retries=10, retry_budget=2)
        engine.decide(1, Exception("err"), "p1", policy)
        engine.decide(2, Exception("err"), "p1", policy)
        decision = engine.decide(3, Exception("err"), "p1", policy)
        assert decision.action == RetryAction.ABORT
        assert "budget" in decision.reason

    def test_exponential_backoff(self):
        engine = RetryEngine()
        policy = RetryPolicy(max_retries=4, base_delay=1.0, backoff_factor=2.0, jitter=0.0)
        d1 = engine.decide(1, Exception("err"), "p1", policy)
        d2 = engine.decide(2, Exception("err"), "p1", policy)
        d3 = engine.decide(3, Exception("err"), "p1", policy)
        assert d1.delay_seconds == 1.0
        assert d2.delay_seconds == 2.0
        assert d3.delay_seconds == 4.0

    def test_delay_capped_at_max(self):
        engine = RetryEngine()
        policy = RetryPolicy(base_delay=10.0, backoff_factor=10.0, max_delay=30.0, jitter=0.0)
        decision = engine.decide(3, Exception("err"), "p1", policy)
        assert decision.delay_seconds <= 30.0

    def test_retry_after_header(self):
        engine = RetryEngine()
        policy = RetryPolicy(base_delay=1.0, jitter=0.0)
        decision = engine.decide(1, Exception("429"), "p1", policy, retry_after_header="5")
        assert decision.delay_seconds >= 5.0

    def test_execute_with_retry_success(self):
        engine = RetryEngine()
        mock_fn = MagicMock(return_value="success")
        success, result, error, attempts = engine.execute_with_retry(mock_fn, "p1")
        assert success == True
        assert result == "success"
        assert attempts == 1

    def test_execute_with_retry_failure_then_success(self):
        engine = RetryEngine()
        call_count = [0]
        def flaky_fn():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("transient error")
            return "success"
        success, result, error, attempts = engine.execute_with_retry(
            flaky_fn, "p1",
            policy=RetryPolicy(max_retries=3, base_delay=0.01, jitter=0.0),
        )
        assert success == True
        assert result == "success"
        assert attempts == 2

    def test_execute_with_retry_all_fail(self):
        engine = RetryEngine()
        def always_fail():
            raise Exception("permanent error")
        success, result, error, attempts = engine.execute_with_retry(
            always_fail, "p1",
            policy=RetryPolicy(max_retries=2, base_delay=0.01, jitter=0.0),
        )
        assert success == False
        assert attempts == 2

    def test_get_attempts(self):
        engine = RetryEngine()
        engine.decide(1, Exception("err"), "p1")
        engine.decide(2, Exception("err"), "p1")
        attempts = engine.get_attempts("p1")
        assert len(attempts) == 2
        assert attempts[0].attempt_number == 1
        assert attempts[1].attempt_number == 2

    def test_reset_budget(self):
        engine = RetryEngine()
        policy = RetryPolicy(max_retries=3, retry_budget=2)
        engine.decide(1, Exception("err"), "p1", policy)
        engine.reset_budget("p1")
        decision = engine.decide(1, Exception("err"), "p1", policy)
        assert decision.action == RetryAction.RETRY

    def test_reset_all(self):
        engine = RetryEngine()
        engine.decide(1, Exception("err"), "p1")
        engine.decide(1, Exception("err"), "p2")
        engine.reset_all()
        assert len(engine.get_attempts("p1")) == 0
        assert len(engine.get_attempts("p2")) == 0
