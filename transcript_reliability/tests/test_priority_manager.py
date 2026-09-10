"""Tests for the Priority Manager."""

from __future__ import annotations

from transcript_reliability.priority_manager import PriorityManager
from transcript_reliability.provider_registry import ProviderRegistry
from transcript_reliability.health_monitor import HealthMonitor
from transcript_reliability.circuit_breaker import CircuitBreakerManager
from transcript_reliability.tests.conftest import MockTranscriptProvider


class TestPriorityManager:
    def setup(self, test_config):
        registry = ProviderRegistry(test_config)
        health = HealthMonitor(test_config)
        cb = CircuitBreakerManager(test_config)
        pm = PriorityManager(registry, health, cb, test_config)
        return registry, health, cb, pm

    def test_get_priority_order(self, test_config):
        registry, health, cb, pm = self.setup(test_config)
        for pid in ["provider_a", "provider_b", "provider_c"]:
            registry.register(MockTranscriptProvider(provider_id=pid))
        order = pm.get_priority_order()
        assert order == ["provider_a", "provider_b", "provider_c"]

    def test_priority_respects_config_order(self, test_config):
        test_config.provider_priority_order = ["provider_c", "provider_a", "provider_b"]
        registry, health, cb, pm = self.setup(test_config)
        for pid in ["provider_a", "provider_b", "provider_c"]:
            registry.register(MockTranscriptProvider(provider_id=pid))
        order = pm.get_priority_order()
        assert order == ["provider_c", "provider_a", "provider_b"]

    def test_priority_skips_disabled(self, test_config):
        test_config.provider_disabled = ["provider_b"]
        registry, health, cb, pm = self.setup(test_config)
        for pid in ["provider_a", "provider_b", "provider_c"]:
            registry.register(MockTranscriptProvider(provider_id=pid))
        order = pm.get_priority_order()
        assert "provider_b" not in order

    def test_priority_skips_unhealthy(self, test_config):
        registry, health, cb, pm = self.setup(test_config)
        for pid in ["provider_a", "provider_b"]:
            registry.register(MockTranscriptProvider(provider_id=pid))
        health.record_failure("provider_b", error_type="timeout")
        health.record_failure("provider_b", error_type="timeout")
        order = pm.get_priority_order(skip_unhealthy=True)
        assert "provider_b" not in order

    def test_priority_skips_open_circuit(self, test_config):
        registry, health, cb, pm = self.setup(test_config)
        for pid in ["provider_a", "provider_b"]:
            registry.register(MockTranscriptProvider(provider_id=pid))
        cb.record_failure("provider_b")
        cb.record_failure("provider_b")
        order = pm.get_priority_order(skip_open_circuit=True)
        assert "provider_b" not in order

    def test_priority_language_override(self, test_config):
        test_config.provider_language_overrides["hi"] = ["deepgram", "assemblyai"]
        registry, health, cb, pm = self.setup(test_config)
        registry.register(MockTranscriptProvider(provider_id="deepgram"))
        registry.register(MockTranscriptProvider(provider_id="assemblyai"))
        order = pm.get_priority_order(language="hi")
        assert order == ["deepgram", "assemblyai"]

    def test_get_providers_in_order(self, test_config):
        registry, health, cb, pm = self.setup(test_config)
        for pid in ["provider_a", "provider_b"]:
            registry.register(MockTranscriptProvider(provider_id=pid))
        providers = pm.get_providers_in_order()
        assert len(providers) == 2
        assert providers[0].provider_id == "provider_a"
        assert providers[1].provider_id == "provider_b"

    def test_set_priority_order(self, test_config):
        registry, health, cb, pm = self.setup(test_config)
        for pid in ["x", "y", "z"]:
            registry.register(MockTranscriptProvider(provider_id=pid))
        pm.set_priority_order(["z", "x", "y"])
        order = pm.get_priority_order()
        assert order == ["z", "x", "y"]

    def test_set_language_override(self, test_config):
        registry, health, cb, pm = self.setup(test_config)
        pm.set_language_override("fr", ["deepgram"])
        order = pm.get_priority_for_language("fr")
        assert order == ["deepgram"]

    def test_priority_with_all_skipped(self, test_config):
        test_config.provider_disabled = ["provider_a", "provider_b", "provider_c"]
        registry, health, cb, pm = self.setup(test_config)
        for pid in ["provider_a", "provider_b", "provider_c"]:
            registry.register(MockTranscriptProvider(provider_id=pid))
        order = pm.get_priority_order()
        assert order == []
