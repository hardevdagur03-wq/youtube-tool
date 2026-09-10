from __future__ import annotations

import time

from observability.performance_monitor import PerformanceMonitor


class TestPerformanceMonitor:
    def test_record(self):
        pm = PerformanceMonitor()
        pm.record("test_op", 100.0, module="test")
        summary = pm.get_summary()
        assert "test_op" in summary
        assert summary["test_op"]["call_count"] == 1

    def test_record_multiple(self):
        pm = PerformanceMonitor(slow_threshold_ms=1000.0)
        for _ in range(5):
            pm.record("multi_op", 50.0)
        summary = pm.get_summary("multi_op")
        assert summary["multi_op"]["call_count"] == 5
        assert summary["multi_op"]["avg_duration_ms"] == 50.0

    def test_percentiles(self):
        pm = PerformanceMonitor()
        for i in range(1, 101):
            pm.record("pct_op", float(i))
        summary = pm.get_summary("pct_op")
        s = summary["pct_op"]
        assert s["p50_ms"] == 50.5
        assert abs(s["p95_ms"] - 95.0) <= 1.0
        assert abs(s["p99_ms"] - 99.0) <= 1.0

    def test_slow_operations(self):
        pm = PerformanceMonitor(slow_threshold_ms=50.0)
        pm.record("fast", 10.0)
        pm.record("slow", 100.0)
        slow = pm.get_slow_operations()
        assert len(slow) == 1
        assert slow[0]["operation"] == "slow"

    def test_get_aggregate_summary(self):
        pm = PerformanceMonitor(slow_threshold_ms=1000.0)
        pm.record("op1", 100.0, module="mod_a")
        pm.record("op2", 200.0, module="mod_b")
        agg = pm.get_aggregate_summary()
        assert agg["total_samples"] == 2
        assert agg["avg_duration_ms"] == 150.0

    def test_clear(self):
        pm = PerformanceMonitor()
        pm.record("op", 100.0)
        pm.clear()
        assert pm.get_aggregate_summary() == {}

    def test_slow_threshold_setter(self):
        pm = PerformanceMonitor(slow_threshold_ms=500.0)
        assert pm.slow_threshold_ms == 500.0
        pm.slow_threshold_ms = 1000.0
        assert pm.slow_threshold_ms == 1000.0
