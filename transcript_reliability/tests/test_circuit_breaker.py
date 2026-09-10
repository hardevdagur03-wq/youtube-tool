"""Tests for the Circuit Breaker."""

from __future__ import annotations

import time

import pytest

from transcript_reliability.circuit_breaker import CircuitBreaker, CircuitBreakerManager
from transcript_reliability.constants import CircuitState


class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED

    def test_allow_request_when_closed(self):
        cb = CircuitBreaker("test")
        assert cb.allow_request() == True

    def test_open_after_failures(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_block_request_when_open(self):
        cb = CircuitBreaker("test", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.allow_request() == False

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.05)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() == False
        time.sleep(0.06)
        assert cb.allow_request() == True
        assert cb.state == CircuitState.HALF_OPEN

    def test_close_after_success_in_half_open(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.05, success_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.06)
        cb.allow_request()  # transitions to half-open
        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_reopen_after_failure_in_half_open(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.05)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.06)
        cb.allow_request()  # transitions to half-open
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_half_open_probe_limits(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.05, half_open_max_probes=2)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.06)
        assert cb.allow_request() == True   # transition to half-open (not counted as probe)
        assert cb.allow_request() == True   # probe 1
        assert cb.allow_request() == True   # probe 2
        assert cb.allow_request() == False  # max probes reached

    def test_reset(self):
        cb = CircuitBreaker("test", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() == True

    def test_get_state_info(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        info = cb.get_state_info()
        assert info.provider_id == "test"
        assert info.state == CircuitState.CLOSED
        assert info.failure_threshold == 3

    def test_record_success_in_closed_resets_counter(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED  # Not enough consecutive failures


class TestCircuitBreakerManager:
    def _make_manager(self, threshold=2):
        """Helper to create manager with low thresholds for testing."""
        mgr = CircuitBreakerManager()
        # Override the default breaker creation with low threshold
        cb = CircuitBreaker("test", failure_threshold=threshold, recovery_timeout=0.05)
        mgr._breakers["test"] = cb
        # Also for fresh provider tests
        cb2 = CircuitBreaker("fresh", failure_threshold=threshold, recovery_timeout=0.05)
        mgr._breakers["fresh"] = cb2
        return mgr

    def _make_p1_p2_manager(self, threshold=2):
        mgr = CircuitBreakerManager()
        mgr._breakers["p1"] = CircuitBreaker("p1", failure_threshold=threshold, recovery_timeout=0.05)
        mgr._breakers["p2"] = CircuitBreaker("p2", failure_threshold=threshold, recovery_timeout=0.05)
        return mgr

    def test_get_breaker_creates_new(self):
        mgr = CircuitBreakerManager()
        cb = mgr.get_breaker("test")
        assert cb.state == CircuitState.CLOSED

    def test_get_breaker_reuses_existing(self):
        mgr = CircuitBreakerManager()
        cb1 = mgr.get_breaker("test")
        cb2 = mgr.get_breaker("test")
        assert cb1 is cb2

    def test_allow_request(self):
        mgr = CircuitBreakerManager()
        assert mgr.allow_request("test") == True

    def test_record_success_failure(self):
        mgr = self._make_manager(threshold=2)
        mgr.record_failure("test")
        mgr.record_failure("test")
        assert mgr.is_open("test") == True
        assert mgr.allow_request("test") == False

    def test_is_open(self):
        mgr = self._make_manager(threshold=2)
        assert mgr.is_open("fresh") == False
        mgr.record_failure("test")
        mgr.record_failure("test")
        assert mgr.is_open("test") == True

    def test_get_state(self):
        mgr = CircuitBreakerManager()
        state = mgr.get_state("test")
        assert state.provider_id == "test"
        assert state.state == CircuitState.CLOSED

    def test_get_all_states(self):
        mgr = CircuitBreakerManager()
        mgr.get_breaker("p1")
        mgr.get_breaker("p2")
        states = mgr.get_all_states()
        assert len(states) == 2

    def test_reset(self):
        mgr = self._make_manager(threshold=2)
        mgr.record_failure("test")
        mgr.record_failure("test")
        assert mgr.is_open("test") == True
        mgr.reset("test")
        assert mgr.is_open("test") == False

    def test_reset_all(self):
        mgr = self._make_p1_p2_manager(threshold=2)
        mgr.record_failure("p1")
        mgr.record_failure("p1")
        mgr.record_failure("p2")
        mgr.record_failure("p2")
        mgr.reset_all()
        assert mgr.is_open("p1") == False
        assert mgr.is_open("p2") == False
