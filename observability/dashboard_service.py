from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from observability.cost_tracker import CostTracker
from observability.error_tracker import ErrorTracker
from observability.health_checks import HealthCheckRegistry
from observability.logger import get_logger
from observability.performance_monitor import PerformanceMonitor
from observability.token_metrics import TokenMetricsCollector


class DashboardService:
    def __init__(
        self,
        token_collector: TokenMetricsCollector | None = None,
        cost_tracker: CostTracker | None = None,
        performance_monitor: PerformanceMonitor | None = None,
        error_tracker: ErrorTracker | None = None,
        health_registry: HealthCheckRegistry | None = None,
    ):
        self._tokens = token_collector
        self._costs = cost_tracker
        self._perf = performance_monitor
        self._errors = error_tracker
        self._health = health_registry
        self._logger = get_logger(__name__)

    def get_executive_summary(self) -> dict[str, Any]:
        return {
            "health": self._health.get_summary() if self._health else {},
            "errors": self._errors.get_error_summary() if self._errors else {},
            "performance": self._perf.get_aggregate_summary() if self._perf else {},
            "tokens": self._tokens.get_summary().to_dict() if self._tokens else {},
            "costs": self._costs.get_summary().to_dict() if self._costs else {},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_developer_dashboard(self, hours: int = 24) -> dict[str, Any]:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        return {
            "recent_errors": self._errors.get_recent_errors(50) if self._errors else [],
            "slow_operations": self._perf.get_slow_operations() if self._perf else [],
            "performance_by_operation": self._perf.get_summary() if self._perf else {},
            "token_usage": self._tokens.get_summary(since=since) if self._tokens else {},
        }

    def get_operations_dashboard(self) -> dict[str, Any]:
        return {
            "health_all": self._health.run_all() if self._health else [],
            "worker_status": {},
            "queue_depth": {},
            "system_resources": self._get_system_resources(),
            "recent_alerts": [],
        }

    def get_ai_usage_dashboard(self) -> dict[str, Any]:
        return {
            "by_model": self._tokens.get_by_model() if self._tokens else {},
            "by_prompt": self._tokens.get_by_prompt() if self._tokens else {},
            "daily_usage": self._tokens.get_daily_usage() if self._tokens else [],
            "cache_savings": self._tokens.get_cache_savings() if self._tokens else {},
        }

    def get_cost_dashboard(self) -> dict[str, Any]:
        return {
            "summary": self._costs.get_summary() if self._costs else {},
            "daily_costs": self._costs.get_daily_costs() if self._costs else [],
            "by_project": self._costs.get_by_project() if self._costs else {},
            "estimated_monthly": self._costs.get_estimated_monthly_cost() if self._costs else 0.0,
            "cumulative": self._costs.get_cumulative_cost() if self._costs else 0.0,
        }

    def get_pipeline_dashboard(self) -> dict[str, Any]:
        return {
            "pipeline_metrics": {},
            "stage_metrics": {},
            "retry_metrics": {},
        }

    def get_cache_dashboard(self) -> dict[str, Any]:
        return {
            "hit_rate": 0.0,
            "miss_rate": 0.0,
            "memory_usage_mb": 0.0,
        }

    def get_database_dashboard(self) -> dict[str, Any]:
        return {
            "connection_pool": {},
            "slow_queries": [],
            "transaction_metrics": {},
        }

    def _get_system_resources(self) -> dict[str, Any]:
        try:
            import psutil
            mem = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=0.1)
            disk = psutil.disk_usage(".")
            return {
                "cpu_percent": cpu,
                "memory_percent": mem.percent,
                "memory_available_mb": round(mem.available / (1024 ** 2), 1),
                "disk_free_gb": round(disk.free / (1024 ** 3), 2),
                "disk_percent": disk.percent,
            }
        except ImportError:
            return {}
