from __future__ import annotations

import time

import pytest

from observability.config import ObservabilityConfig
from observability.metrics import MetricsManager


class TestMetricsManager:
    def test_initialization(self):
        config = ObservabilityConfig(metrics_enabled=False)
        mm = MetricsManager(config)
        mm.initialize()
        assert mm._initialized is False

    def test_counter(self):
        config = ObservabilityConfig(metrics_enabled=False)
        mm = MetricsManager(config)
        c = mm.counter("test_counter", "label1")
        assert c is not None
        c.labels(label1="val1").inc()
        assert c.labels(label1="val1")._value.get() == 1.0

    def test_gauge(self):
        config = ObservabilityConfig(metrics_enabled=False)
        mm = MetricsManager(config)
        g = mm.gauge("test_gauge", "label1")
        g.labels(label1="val1").set(42)
        assert g.labels(label1="val1")._value.get() == 42.0

    def test_histogram(self):
        config = ObservabilityConfig(metrics_enabled=False)
        mm = MetricsManager(config)
        h = mm.histogram("test_histogram", "label1")
        h.labels(label1="val1").observe(0.5)
        assert h.labels(label1="val1")._sum.get() == 0.5

    def test_inc(self):
        config = ObservabilityConfig(metrics_enabled=False)
        mm = MetricsManager(config)
        mm.inc("test_inc", label="val")
        # Just check no exception

    def test_set(self):
        config = ObservabilityConfig(metrics_enabled=False)
        mm = MetricsManager(config)
        mm.set("test_set", 99, label="val")

    def test_observe(self):
        config = ObservabilityConfig(metrics_enabled=False)
        mm = MetricsManager(config)
        mm.observe("test_observe", 1.5, label="val")

    def test_observe_latency(self):
        config = ObservabilityConfig(metrics_enabled=False)
        mm = MetricsManager(config)
        record = mm.observe_latency("test_latency", label="val")
        time.sleep(0.01)
        record()

    def test_measure_duration(self):
        config = ObservabilityConfig(metrics_enabled=False)
        mm = MetricsManager(config)
        with mm.measure_duration("test_duration", label="val"):
            time.sleep(0.01)

    def test_instrument_decorator(self):
        config = ObservabilityConfig(metrics_enabled=False)
        mm = MetricsManager(config)

        @mm.instrument("test_decorator", label_names=("param",))
        def my_func(param: str) -> str:
            return f"hello {param}"

        result = my_func(param="world")
        assert result == "hello world"

    def test_instrument_decorator_error(self):
        config = ObservabilityConfig(metrics_enabled=False)
        mm = MetricsManager(config)

        @mm.instrument("test_error")
        def failing_func():
            raise ValueError("boom")

        with pytest.raises(ValueError):
            failing_func()
