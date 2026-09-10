from __future__ import annotations

from observability.config import ObservabilityConfig
from observability.tracing import TracingManager, generate_trace_id, generate_span_id


class TestTracingManager:
    def test_initialization(self):
        config = ObservabilityConfig(tracing_enabled=True)
        tm = TracingManager(config)
        assert tm._initialized is False

    def test_initialize(self):
        config = ObservabilityConfig(tracing_enabled=False)
        tm = TracingManager(config)
        tm.initialize()
        assert tm._initialized is False

    def test_get_tracer(self):
        config = ObservabilityConfig(tracing_enabled=False)
        tm = TracingManager(config)
        tracer = tm.get_tracer()
        assert tracer is not None

    def test_inject_headers_when_not_tracing(self):
        config = ObservabilityConfig(tracing_enabled=False)
        tm = TracingManager(config)
        headers = tm.inject_headers()
        assert isinstance(headers, dict)

    def test_generate_ids(self):
        tid = generate_trace_id()
        sid = generate_span_id()
        assert len(tid) > 0
        assert len(sid) > 0
        assert tid != sid
