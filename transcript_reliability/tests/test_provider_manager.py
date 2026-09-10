"""Tests for the Provider Manager."""

from __future__ import annotations

from transcript_reliability.provider_manager import ProviderManager
from transcript_reliability.provider_registry import ProviderRegistry
from transcript_reliability.health_monitor import HealthMonitor
from transcript_reliability.circuit_breaker import CircuitBreakerManager
from transcript_reliability.constants import ProviderStatus, ProviderCapability
from transcript_reliability.tests.conftest import MockTranscriptProvider


class TestProviderManager:
    def setup(self, test_config):
        registry = ProviderRegistry(test_config)
        health = HealthMonitor(test_config)
        cb = CircuitBreakerManager(test_config)
        pm = ProviderManager(registry, health, cb, test_config)
        return registry, health, cb, pm

    def test_enable_disable_provider(self, test_config):
        registry, health, cb, pm = self.setup(test_config)
        provider = MockTranscriptProvider(provider_id="test_prov")
        registry.register(provider)

        pm.disable_provider("test_prov")
        assert pm.is_provider_enabled("test_prov") == False

        pm.enable_provider("test_prov")
        assert pm.is_provider_enabled("test_prov") == True

    def test_get_provider_info(self, test_config):
        registry, health, cb, pm = self.setup(test_config)
        provider = MockTranscriptProvider(provider_id="test_prov", name="Test Provider")
        registry.register(provider)
        info = pm.get_provider_info("test_prov")
        assert info.provider_id == "test_prov"
        assert info.name == "Test Provider"

    def test_get_provider_health(self, test_config):
        registry, health, cb, pm = self.setup(test_config)
        provider = MockTranscriptProvider(provider_id="test_prov")
        registry.register(provider)
        health.record_success("test_prov", latency_ms=100)
        health_status = pm.get_provider_health("test_prov")
        assert health_status.total_requests == 1
        assert health_status.success_rate == 1.0

    def test_get_provider_status_healthy(self, test_config):
        registry, health, cb, pm = self.setup(test_config)
        provider = MockTranscriptProvider(provider_id="test_prov")
        registry.register(provider)
        health.record_success("test_prov")
        status = pm.get_provider_status("test_prov")
        assert status == ProviderStatus.HEALTHY

    def test_get_provider_status_circuit_open(self, test_config):
        registry, health, cb, pm = self.setup(test_config)
        provider = MockTranscriptProvider(provider_id="test_prov")
        registry.register(provider)
        cb.record_failure("test_prov")
        cb.record_failure("test_prov")
        status = pm.get_provider_status("test_prov")
        assert status == ProviderStatus.UNHEALTHY

    def test_list_providers(self, test_config):
        registry, health, cb, pm = self.setup(test_config)
        for p in [MockTranscriptProvider(pid) for pid in ["a", "b", "c"]]:
            registry.register(p)
        providers = pm.list_providers()
        assert len(providers) == 3

    def test_list_healthy_providers(self, test_config):
        registry, health, cb, pm = self.setup(test_config)
        a = MockTranscriptProvider(provider_id="a")
        b = MockTranscriptProvider(provider_id="b")
        registry.register(a)
        registry.register(b)
        health.record_success("a", latency_ms=10)
        health.record_success("b", latency_ms=10)
        healthy = pm.list_healthy_providers()
        assert len(healthy) == 2

    def test_list_healthy_skips_unhealthy(self, test_config):
        registry, health, cb, pm = self.setup(test_config)
        a = MockTranscriptProvider(provider_id="a")
        b = MockTranscriptProvider(provider_id="b")
        registry.register(a)
        registry.register(b)
        health.record_success("a", latency_ms=10)
        health.record_failure("b", error_type="timeout")
        health.record_failure("b", error_type="timeout")
        healthy = pm.list_healthy_providers()
        assert len(healthy) == 1
        assert healthy[0].provider_id == "a"

    def test_capability_summary(self, test_config):
        registry, health, cb, pm = self.setup(test_config)
        a = MockTranscriptProvider(provider_id="a", capabilities=[ProviderCapability.CAPTIONS])
        b = MockTranscriptProvider(provider_id="b", capabilities=[ProviderCapability.STT])
        registry.register(a)
        registry.register(b)
        summary = pm.get_capability_summary()
        assert "captions" in summary["a"]
        assert "stt" in summary["b"]

    def test_cost_summary(self, test_config):
        registry, health, cb, pm = self.setup(test_config)
        registry.register(MockTranscriptProvider(provider_id="free", cost_per_minute=0.0))
        registry.register(MockTranscriptProvider(provider_id="paid", cost_per_minute=0.01))
        costs = pm.get_cost_summary()
        assert costs["free"] == 0.0

    def test_latency_summary(self, test_config):
        registry, health, cb, pm = self.setup(test_config)
        p = MockTranscriptProvider(provider_id="test_prov")
        registry.register(p)
        health.record_success("test_prov", latency_ms=100)
        health.record_success("test_prov", latency_ms=200)
        summary = pm.get_latency_summary()
        assert summary["test_prov"]["avg_ms"] == 150.0
