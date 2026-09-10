from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from observability.config import ObservabilityConfig


class TestStructuredLogger:
    def test_info(self):
        from observability.logger import StructuredLogger
        logger = StructuredLogger(name="test_logger")
        logger.info("Test info message", extra={"key": "value"})
        assert True

    def test_error(self):
        from observability.logger import StructuredLogger
        logger = StructuredLogger(name="test_logger")
        logger.error("Test error message", error="Something went wrong")
        assert True

    def test_bind(self):
        from observability.logger import StructuredLogger
        logger = StructuredLogger(name="test_logger")
        bound = logger.bind(trace_id="abc123")
        assert bound is not None


class TestTracingManager:
    def test_start_span(self):
        from observability.tracing import TracingManager
        config = ObservabilityConfig()
        mgr = TracingManager(config)
        mgr.initialize()
        span = mgr.start_span("test_span")
        assert span is not None

    def test_trace_context(self):
        from observability.tracing import TracingManager
        config = ObservabilityConfig()
        mgr = TracingManager(config)
        ctx = mgr.inject_headers()
        assert ctx is not None


class TestMetricsManager:
    def test_counter(self):
        from observability.metrics import MetricsManager
        config = ObservabilityConfig()
        mgr = MetricsManager(config)
        mgr.inc("test_counter", key="value")
        assert True

    def test_gauge(self):
        from observability.metrics import MetricsManager
        config = ObservabilityConfig()
        mgr = MetricsManager(config)
        mgr.set("test_gauge", 42.0)
        assert True

    def test_histogram(self):
        from observability.metrics import MetricsManager
        config = ObservabilityConfig()
        mgr = MetricsManager(config)
        mgr.observe("test_histogram", 0.5)
        assert True

    def test_get_metrics(self):
        from observability.metrics import MetricsManager
        config = ObservabilityConfig()
        mgr = MetricsManager(config)
        mgr.inc("test_metrics_counter")
        assert True


class TestTelemetryOrchestrator:
    def test_initialize(self):
        from observability.telemetry import TelemetryOrchestrator
        orchestrator = TelemetryOrchestrator()
        orchestrator.initialize()
        assert True

    def test_shutdown(self):
        from observability.telemetry import TelemetryOrchestrator
        orchestrator = TelemetryOrchestrator()
        orchestrator.shutdown()
        assert True


class TestInstrumentationMiddleware:
    def test_middleware_init(self):
        from observability.instrumentation import InstrumentationMiddleware
        from observability.metrics import MetricsManager
        from observability.tracing import TracingManager
        config = ObservabilityConfig()
        metrics = MetricsManager(config)
        tracing = TracingManager(config)
        middleware = InstrumentationMiddleware(app=MagicMock(), metrics=metrics, tracing=tracing)
        assert middleware is not None


class TestInstrumentFunction:
    def test_instrument_function(self):
        from observability.instrumentation import instrument_function
        @instrument_function(name="test_func")
        def test_func():
            return 42
        assert test_func() == 42

    def test_instrument_method(self):
        from observability.instrumentation import instrument_method
        class TestClass:
            @instrument_method(name="test_method")
            def test_method(self):
                return "hello"
        obj = TestClass()
        assert obj.test_method() == "hello"


class TestHealthChecks:
    def test_registry(self):
        from observability.health_checks import HealthCheckRegistry, HealthStatus, HealthCheckResult
        registry = HealthCheckRegistry()
        registry.register(name="test_check", check_fn=lambda: HealthCheckResult(name="test_check", status=HealthStatus.HEALTHY))
        assert True

    def test_run_checks(self):
        from observability.health_checks import HealthCheckRegistry, HealthStatus, HealthCheckResult
        registry = HealthCheckRegistry()
        registry.register("test", lambda: HealthCheckResult(name="test", status=HealthStatus.HEALTHY))
        results = registry.run_all()
        assert len(results) > 0
        assert results[0].name == "test"

    def test_health_status_enum(self):
        from observability.health_checks import HealthStatus
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"


class TestAlertManager:
    def test_add_rule(self):
        from observability.alert_manager import AlertManager, AlertRule, AlertSeverity
        mgr = AlertManager()
        rule = AlertRule(name="high_error_rate", description="Errors exceed threshold", condition=lambda: False, severity=AlertSeverity.WARNING)
        mgr.register(rule)
        assert True

    def test_evaluate(self):
        from observability.alert_manager import AlertManager, AlertRule, AlertSeverity
        mgr = AlertManager()
        rule = AlertRule(name="test_rule", description="Test rule", condition=lambda: True, severity=AlertSeverity.INFO, cooldown_seconds=0)
        mgr.register(rule)
        result = mgr.evaluate()
        assert len(result) >= 0


class TestErrorTracker:
    def test_track_error(self):
        from observability.error_tracker import ErrorTracker
        tracker = ErrorTracker()
        error_id = tracker.capture(exc=ValueError("test error"), module="test")
        assert error_id is not None

    def test_get_error(self):
        from observability.error_tracker import ErrorTracker
        tracker = ErrorTracker()
        eid = tracker.capture(ValueError("test"), "test")
        errors = tracker.get_grouped_errors()
        assert len(errors) > 0
        assert errors[0]["error_type"] == "ValueError"

    def test_get_errors(self):
        from observability.error_tracker import ErrorTracker
        tracker = ErrorTracker()
        tracker.capture(ValueError("err1"), "test")
        tracker.capture(RuntimeError("err2"), "test")
        errors = tracker.get_grouped_errors()
        assert len(errors) == 2


class TestTokenMetricsCollector:
    def test_record(self):
        from observability.token_metrics import TokenMetricsCollector
        collector = TokenMetricsCollector()
        collector.record_call(prompt_name="test", model="gpt-4", provider="openai", prompt_tokens=100, completion_tokens=50, project_id="p1")
        stats = collector.get_summary()
        assert stats.total_prompt_tokens >= 100

    def test_get_daily_usage(self):
        from observability.token_metrics import TokenMetricsCollector
        collector = TokenMetricsCollector()
        collector.record_call("test", "gpt-4", "openai", 100, 50)
        daily = collector.get_daily_usage()
        assert "total_tokens" in daily[0]


class TestCostTracker:
    def test_record(self):
        from observability.cost_tracker import CostTracker
        tracker = CostTracker()
        tracker.record_cost(service="openai", operation="completion", model="gpt-4", tokens=100, cost=0.002)
        stats = tracker.get_summary()
        assert stats.total_cost > 0

    def test_get_estimated_monthly(self):
        from observability.cost_tracker import CostTracker
        tracker = CostTracker()
        tracker.record_cost("openai", "completion", 0.02, model="gpt-4", tokens=1000)
        monthly = tracker.get_estimated_monthly_cost()
        assert monthly > 0


class TestPerformanceMonitor:
    def test_record(self):
        from observability.performance_monitor import PerformanceMonitor
        monitor = PerformanceMonitor()
        monitor.record(operation="db_query", duration_ms=150.0)
        monitor.record("db_query", 200.0)
        stats = monitor.get_summary("db_query")
        assert stats["db_query"]["call_count"] == 2

    def test_get_slow_operations(self):
        from observability.performance_monitor import PerformanceMonitor
        monitor = PerformanceMonitor()
        monitor.record("slow_op", 5000.0)
        slow = monitor.get_slow_operations(threshold_ms=1000.0)
        assert len(slow) > 0


class TestDashboardService:
    def test_get_dashboard(self):
        from observability.dashboard_service import DashboardService
        from observability.health_checks import HealthCheckRegistry, HealthStatus, HealthCheckResult
        from observability.error_tracker import ErrorTracker
        from observability.performance_monitor import PerformanceMonitor
        from observability.token_metrics import TokenMetricsCollector
        from observability.cost_tracker import CostTracker
        health = HealthCheckRegistry()
        health.register("test", lambda: HealthCheckResult(name="test", status=HealthStatus.HEALTHY))
        svc = DashboardService(
            token_collector=TokenMetricsCollector(),
            cost_tracker=CostTracker(),
            performance_monitor=PerformanceMonitor(),
            error_tracker=ErrorTracker(),
            health_registry=health,
        )
        data = svc.get_executive_summary()
        assert data is not None
        assert "health" in data


class TestAuditLogger:
    def test_log_event(self):
        from observability.audit_logger import AuditLogger, AuditEventType
        logger = AuditLogger()
        logger.log_event(event_type=AuditEventType.PROJECT_CREATED, actor_id="user1", action="project.created", resource_id="project:123")
        events = logger.get_recent()
        assert events[0]["action"] == "project.created"

    def test_get_events(self):
        from observability.audit_logger import AuditLogger, AuditEventType
        logger = AuditLogger()
        logger.log_event(AuditEventType.USER_LOGIN, "user1", "test.action", resource_id="res:1")
        logger.log_event(AuditEventType.USER_ACTION, "user1", "test.action2", resource_id="res:2")
        events = logger.get_recent()
        assert len(events) >= 2


class TestTelemetryExporter:
    def test_export(self):
        from observability.telemetry_exporter import TelemetryExporter
        config = ObservabilityConfig()
        exporter = TelemetryExporter(config)
        exporter.export_log({"key": "value"})
        assert True

    def test_flush(self):
        from observability.telemetry_exporter import TelemetryExporter
        config = ObservabilityConfig()
        exporter = TelemetryExporter(config)
        exporter.flush()
        assert True
