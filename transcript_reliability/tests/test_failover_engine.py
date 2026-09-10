"""Tests for the Failover Engine."""

from __future__ import annotations

import pytest

from transcript_reliability.failover_engine import FailoverEngine
from transcript_reliability.provider_registry import ProviderRegistry
from transcript_reliability.priority_manager import PriorityManager
from transcript_reliability.health_monitor import HealthMonitor
from transcript_reliability.circuit_breaker import CircuitBreakerManager
from transcript_reliability.retry_engine import RetryEngine
from transcript_reliability.tests.conftest import MockTranscriptProvider


class TestFailoverEngine:
    def setup(self, test_config):
        registry = ProviderRegistry(test_config)
        health = HealthMonitor(test_config)
        cb = CircuitBreakerManager(test_config)
        retry = RetryEngine(test_config)
        priority = PriorityManager(registry, health, cb, test_config)
        engine = FailoverEngine(registry, priority, health, cb, retry, test_config)
        return registry, engine

    def test_first_provider_succeeds(self, test_config):
        registry, engine = self.setup(test_config)
        a = MockTranscriptProvider(provider_id="provider_a", should_succeed=True)
        b = MockTranscriptProvider(provider_id="provider_b", should_succeed=True)
        registry.register(a)
        registry.register(b)
        result = engine.get_transcript("dQw4w9WgXcQ")
        assert result.success == True
        assert a.call_count == 1
        assert b.call_count == 0

    def test_failover_to_second_provider(self, test_config):
        registry, engine = self.setup(test_config)
        a = MockTranscriptProvider(provider_id="provider_a", should_succeed=False)
        b = MockTranscriptProvider(provider_id="provider_b", should_succeed=True)
        registry.register(a)
        registry.register(b)
        result = engine.get_transcript("dQw4w9WgXcQ")
        assert result.success == True
        assert a.call_count >= 1
        assert b.call_count == 1

    def test_all_providers_fail(self, test_config):
        registry, engine = self.setup(test_config)
        a = MockTranscriptProvider(provider_id="provider_a", should_succeed=False)
        b = MockTranscriptProvider(provider_id="provider_b", should_succeed=False)
        registry.register(a)
        registry.register(b)
        result = engine.get_transcript("dQw4w9WgXcQ")
        assert result.success == False
        assert "All" in result.error or "failed" in result.error

    def test_failover_skips_circuit_open(self, test_config):
        registry, engine = self.setup(test_config)
        a = MockTranscriptProvider(provider_id="provider_a", should_succeed=False)
        b = MockTranscriptProvider(provider_id="provider_b", should_succeed=True)
        registry.register(a)
        registry.register(b)
        engine._circuit_breaker.record_failure("provider_a")
        engine._circuit_breaker.record_failure("provider_a")
        engine._circuit_breaker.record_failure("provider_a")
        engine._circuit_breaker.record_failure("provider_a")
        engine._circuit_breaker.record_failure("provider_a")
        assert engine._circuit_breaker.is_open("provider_a") == True
        result = engine.get_transcript("dQw4w9WgXcQ")
        assert result.success == True
        assert b.call_count == 1

    def test_failover_chain_recorded(self, test_config):
        registry, engine = self.setup(test_config)
        a = MockTranscriptProvider(provider_id="provider_a", should_succeed=False)
        b = MockTranscriptProvider(provider_id="provider_b", should_succeed=True)
        registry.register(a)
        registry.register(b)
        result = engine.get_transcript("dQw4w9WgXcQ")
        assert result.success == True
        steps = result.pipeline_steps or []
        failover_steps = [s for s in steps if isinstance(s, dict) and s.get("name") == "failover"]
        assert len(failover_steps) >= 1
        assert "provider_b" in str(failover_steps)

    def test_no_providers_available(self, test_config):
        registry, engine = self.setup(test_config)
        result = engine.get_transcript("dQw4w9WgXcQ")
        assert result.success == False
        assert "No transcript providers" in result.error

    def test_provider_specific_video_failure(self, test_config):
        registry, engine = self.setup(test_config)
        a = MockTranscriptProvider(
            provider_id="provider_a", should_succeed=True,
            fail_on_video_ids=["bad_video"],
        )
        b = MockTranscriptProvider(provider_id="provider_b", should_succeed=True)
        registry.register(a)
        registry.register(b)
        result = engine.get_transcript("bad_video")
        assert result.success == True
        assert a.call_count >= 1
        assert b.call_count >= 1

    def test_failover_summary(self, test_config):
        registry, engine = self.setup(test_config)
        a = MockTranscriptProvider(provider_id="provider_a", should_succeed=True)
        registry.register(a)
        engine.get_transcript("test123")
        summary = engine.get_failover_summary()
        assert "providers" in summary
        assert "available_count" in summary
