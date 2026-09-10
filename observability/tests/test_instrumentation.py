from __future__ import annotations

from unittest.mock import MagicMock

from observability.config import ObservabilityConfig
from observability.metrics import MetricsManager
from observability.tracing import TracingManager
from observability.instrumentation import (
    InstrumentationContext,
    instrument_function,
    instrument_method,
    instrument_context,
)


class TestInstrumentationContext:
    def test_request_id(self):
        ctx = InstrumentationContext()
        rid = ctx.request_id
        assert len(rid) > 0
        assert ctx.request_id == rid

    def test_set_get(self):
        ctx = InstrumentationContext()
        ctx.set("key1", "val1")
        assert ctx.get("key1") == "val1"
        assert ctx.get("nonexistent") is None

    def test_get_all(self):
        ctx = InstrumentationContext()
        ctx.set("a", 1)
        ctx.set("b", 2)
        all_vals = ctx.get_all()
        assert all_vals == {"a": 1, "b": 2}


class TestInstrumentFunction:
    def test_decorator_success(self):
        metrics = MetricsManager(ObservabilityConfig(metrics_enabled=False))

        @instrument_function("test_success", metrics=metrics)
        def my_func(x: int) -> int:
            return x * 2

        assert my_func(5) == 10

    def test_decorator_failure(self):
        metrics = MetricsManager(ObservabilityConfig(metrics_enabled=False))

        @instrument_function("test_fail", metrics=metrics)
        def failing_func():
            raise ValueError("fail")

        import pytest
        with pytest.raises(ValueError):
            failing_func()


class TestInstrumentMethod:
    def test_method_decorator(self):
        metrics = MetricsManager(ObservabilityConfig(metrics_enabled=False))

        class MyClass:
            def __init__(self):
                self._metrics = metrics

            @instrument_method("my_method")
            def do_something(self, val: str) -> str:
                return f"done {val}"

        obj = MyClass()
        assert obj.do_something("test") == "done test"


class TestInstrumentContext:
    def test_context_manager(self):
        metrics = MetricsManager(ObservabilityConfig(metrics_enabled=False))

        with instrument_context("test_op", metrics=metrics):
            pass  # Should not raise

    def test_context_manager_failure(self):
        metrics = MetricsManager(ObservabilityConfig(metrics_enabled=False))

        import pytest
        with pytest.raises(ValueError):
            with instrument_context("test_fail", metrics=metrics):
                raise ValueError("fail")
