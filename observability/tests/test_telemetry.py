from __future__ import annotations

from observability.config import ObservabilityConfig
from observability.telemetry import TelemetryOrchestrator, get_telemetry


class TestTelemetryOrchestrator:
    def test_initialization(self):
        config = ObservabilityConfig(
            tracing_enabled=False,
            metrics_enabled=False,
            sentry_enabled=False,
        )
        to = TelemetryOrchestrator(config)
        to.initialize()
        assert to._initialized is True
        assert to.tracing is not None
        assert to.metrics is not None

    def test_shutdown(self):
        config = ObservabilityConfig(tracing_enabled=False)
        to = TelemetryOrchestrator(config)
        to.initialize()
        to.shutdown()

    def test_get_logger(self):
        config = ObservabilityConfig(tracing_enabled=False, metrics_enabled=False)
        to = TelemetryOrchestrator(config)
        to.initialize()
        logger = to.get_logger("test_telemetry")
        assert logger is not None

    def test_get_telemetry_singleton(self):
        t1 = get_telemetry()
        t2 = get_telemetry()
        assert t1 is t2
