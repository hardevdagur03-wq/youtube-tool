from __future__ import annotations

from observability import *  # noqa: F401, F403


class TestExports:
    def test_all_symbols_exported(self):
        """Verify all expected symbols are in __all__."""
        from observability import __all__ as exports
        expected = [
            "ObservabilityConfig",
            "StructuredLogger",
            "get_logger",
            "TracingManager",
            "MetricsManager",
            "TelemetryOrchestrator",
            "instrument_fastapi",
            "instrument_function",
            "instrument_method",
            "InstrumentationContext",
            "InstrumentationMiddleware",
            "HealthCheckRegistry",
            "HealthStatus",
            "AlertManager",
            "AlertSeverity",
            "AlertRule",
            "ErrorTracker",
            "TokenMetricsCollector",
            "CostTracker",
            "PerformanceMonitor",
            "DashboardService",
            "AuditLogger",
            "TelemetryExporter",
        ]
        for name in expected:
            assert name in exports, f"{name} not in __all__"
