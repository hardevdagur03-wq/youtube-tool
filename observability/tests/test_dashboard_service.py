from __future__ import annotations

from observability.cost_tracker import CostTracker
from observability.dashboard_service import DashboardService
from observability.error_tracker import ErrorTracker
from observability.health_checks import HealthCheckRegistry, HealthStatus, HealthCheckResult
from observability.performance_monitor import PerformanceMonitor
from observability.token_metrics import TokenMetricsCollector


class TestDashboardService:
    def setup_method(self):
        self.tokens = TokenMetricsCollector()
        self.costs = CostTracker()
        self.perf = PerformanceMonitor()
        self.errors = ErrorTracker()
        self.health = HealthCheckRegistry()
        self.ds = DashboardService(
            token_collector=self.tokens,
            cost_tracker=self.costs,
            performance_monitor=self.perf,
            error_tracker=self.errors,
            health_registry=self.health,
        )

    def test_executive_summary(self):
        summary = self.ds.get_executive_summary()
        assert "health" in summary
        assert "errors" in summary
        assert "performance" in summary
        assert "tokens" in summary
        assert "costs" in summary

    def test_developer_dashboard(self):
        dashboard = self.ds.get_developer_dashboard()
        assert "recent_errors" in dashboard
        assert "slow_operations" in dashboard
        assert "performance_by_operation" in dashboard

    def test_operations_dashboard(self):
        dashboard = self.ds.get_operations_dashboard()
        assert "health_all" in dashboard
        assert "system_resources" in dashboard

    def test_ai_usage_dashboard(self):
        dashboard = self.ds.get_ai_usage_dashboard()
        assert "by_model" in dashboard
        assert "daily_usage" in dashboard
        assert "cache_savings" in dashboard

    def test_cost_dashboard(self):
        dashboard = self.ds.get_cost_dashboard()
        assert "summary" in dashboard
        assert "daily_costs" in dashboard
        assert "estimated_monthly" in dashboard
        assert "cumulative" in dashboard

    def test_with_data(self):
        self.tokens.record_call(prompt_name="test", model="gpt-4o", provider="openai", prompt_tokens=100, completion_tokens=50)
        self.costs.record_cost(service="openai", operation="chat", cost=0.025)
        self.perf.record("pipeline_run", 5000.0)
        import pytest
        try:
            raise ValueError("dash test")
        except ValueError as e:
            self.errors.capture(e)
        self.health.register("ok", lambda: HealthCheckResult(name="ok", status=HealthStatus.HEALTHY))
        summary = self.ds.get_executive_summary()
        assert summary["tokens"]["call_count"] == 1
        assert summary["costs"]["call_count"] == 1
        assert summary["performance"]["total_samples"] == 1
