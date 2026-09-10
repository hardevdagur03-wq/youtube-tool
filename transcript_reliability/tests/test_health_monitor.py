"""Tests for the Health Monitor."""

from __future__ import annotations

import time

from transcript_reliability.health_monitor import HealthMonitor
from transcript_reliability.constants import ProviderStatus


class TestHealthMonitor:
    def test_initial_health_unknown(self):
        hm = HealthMonitor()
        health = hm.get_health("unknown_provider")
        assert health.status == ProviderStatus.UNKNOWN
        assert health.total_requests == 0

    def test_record_success(self):
        hm = HealthMonitor()
        hm.record_success("p1", latency_ms=100)
        health = hm.get_health("p1")
        assert health.total_requests == 1
        assert health.success_rate == 1.0
        assert health.avg_latency_ms == 100.0

    def test_record_failure(self):
        hm = HealthMonitor()
        hm.record_failure("p1", error_type="timeout")
        health = hm.get_health("p1")
        assert health.total_requests == 1
        assert health.success_rate == 0.0
        assert health.failure_count == 1

    def test_mixed_success_failure(self):
        hm = HealthMonitor()
        hm.record_success("p1", latency_ms=50)
        hm.record_success("p1", latency_ms=150)
        hm.record_failure("p1", error_type="timeout")
        health = hm.get_health("p1")
        assert health.total_requests == 3
        assert health.success_rate == 2 / 3
        assert health.avg_latency_ms == 100.0
        assert health.failure_count == 1

    def test_status_healthy(self):
        hm = HealthMonitor()
        for _ in range(10):
            hm.record_success("p1", latency_ms=50)
        health = hm.get_health("p1")
        assert health.status == ProviderStatus.HEALTHY

    def test_status_degraded(self, test_config):
        test_config.health_downgrade_threshold = 0.8
        hm = HealthMonitor(test_config)
        for _ in range(7):
            hm.record_success("p1")
        for _ in range(3):
            hm.record_failure("p1")
        health = hm.get_health("p1")
        assert health.status == ProviderStatus.DEGRADED

    def test_status_unhealthy(self, test_config):
        test_config.health_disable_threshold = 0.3
        hm = HealthMonitor(test_config)
        for _ in range(2):
            hm.record_success("p1")
        for _ in range(8):
            hm.record_failure("p1")
        health = hm.get_health("p1")
        assert health.status == ProviderStatus.UNHEALTHY

    def test_latency_percentiles(self):
        hm = HealthMonitor()
        for lat in [50, 100, 150, 200, 250, 300, 350, 400, 450, 500]:
            hm.record_success("p1", latency_ms=lat)
        health = hm.get_health("p1")
        assert health.avg_latency_ms == 275.0  # average of 50..500
        assert health.p95_latency_ms > 0
        assert health.p99_latency_ms > 0

    def test_recent_errors_tracked(self):
        hm = HealthMonitor()
        hm.record_failure("p1", error_type="timeout")
        health = hm.get_health("p1")
        assert len(health.recent_errors) == 1
        assert health.recent_errors[0]["error_type"] == "timeout"

    def test_get_stats(self):
        hm = HealthMonitor()
        hm.record_success("p1", latency_ms=100)
        hm.record_success("p1", latency_ms=200)
        stats = hm.get_stats("p1")
        assert stats.total_requests == 2
        assert stats.successful_requests == 2
        assert stats.avg_latency_ms == 150.0

    def test_get_all_health(self):
        hm = HealthMonitor()
        hm.record_success("p1")
        hm.record_success("p2")
        all_h = hm.get_all_health()
        assert len(all_h) == 2

    def test_get_health_summary(self):
        hm = HealthMonitor()
        hm.record_success("p1")
        summary = hm.get_health_summary()
        assert "providers" in summary
        assert summary["healthy_count"] >= 1

    def test_reset(self):
        hm = HealthMonitor()
        hm.record_success("p1")
        hm.reset("p1")
        health = hm.get_health("p1")
        assert health.status == ProviderStatus.UNKNOWN
        assert health.total_requests == 0

    def test_reset_all(self):
        hm = HealthMonitor()
        hm.record_success("p1")
        hm.record_success("p2")
        hm.reset_all()
        assert len(hm.get_all_health()) == 0

    def test_quota_tracking(self):
        hm = HealthMonitor()
        hm.record_success("p1", quota_remaining=0.5)
        health = hm.get_health("p1")
        assert health.quota_usage == 0.5
