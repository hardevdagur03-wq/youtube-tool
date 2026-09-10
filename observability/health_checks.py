from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    name: str
    status: HealthStatus
    detail: str = ""
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "detail": self.detail,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


CheckFn = Callable[[], HealthCheckResult]


class HealthCheckRegistry:
    def __init__(self):
        self._checks: dict[str, CheckFn] = {}

    def register(self, name: str, check_fn: CheckFn) -> None:
        self._checks[name] = check_fn

    def unregister(self, name: str) -> None:
        self._checks.pop(name, None)

    def run_all(self) -> list[HealthCheckResult]:
        results: list[HealthCheckResult] = []
        for name, check_fn in self._checks.items():
            start = time.monotonic()
            try:
                result = check_fn()
            except Exception as exc:
                result = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    detail=str(exc),
                )
            result.duration_ms = (time.monotonic() - start) * 1000
            results.append(result)
        return results

    def run(self, name: str) -> HealthCheckResult | None:
        check_fn = self._checks.get(name)
        if not check_fn:
            return None
        start = time.monotonic()
        try:
            result = check_fn()
        except Exception as exc:
            result = HealthCheckResult(name=name, status=HealthStatus.UNHEALTHY, detail=str(exc))
        result.duration_ms = (time.monotonic() - start) * 1000
        return result

    def get_summary(self) -> dict[str, Any]:
        results = self.run_all()
        statuses = [r.status for r in results]
        overall = HealthStatus.HEALTHY
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            overall = HealthStatus.DEGRADED
        return {
            "overall": overall.value,
            "healthy": sum(1 for s in statuses if s == HealthStatus.HEALTHY),
            "degraded": sum(1 for s in statuses if s == HealthStatus.DEGRADED),
            "unhealthy": sum(1 for s in statuses if s == HealthStatus.UNHEALTHY),
            "total": len(results),
            "checks": [r.to_dict() for r in results],
        }


_registry: HealthCheckRegistry | None = None


def get_health_registry() -> HealthCheckRegistry:
    global _registry
    if _registry is None:
        _registry = HealthCheckRegistry()
    return _registry


def create_database_health_check(session_getter: Callable[[], Any]) -> CheckFn:
    def check() -> HealthCheckResult:
        try:
            session = session_getter()
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                result = loop.run_until_complete(session.execute("SELECT 1"))
            except RuntimeError:
                import asyncio
                result = asyncio.run(session.execute("SELECT 1"))
            return HealthCheckResult(name="database", status=HealthStatus.HEALTHY, detail="database_ok")
        except Exception as exc:
            return HealthCheckResult(name="database", status=HealthStatus.UNHEALTHY, detail=str(exc))
    return check


def create_redis_health_check(redis_client_getter: Callable[[], Any]) -> CheckFn:
    def check() -> HealthCheckResult:
        try:
            client = redis_client_getter()
            client.ping()
            return HealthCheckResult(name="redis", status=HealthStatus.HEALTHY, detail="redis_ok")
        except Exception as exc:
            return HealthCheckResult(name="redis", status=HealthStatus.UNHEALTHY, detail=str(exc))
    return check


def create_disk_health_check(path: str = ".", threshold_gb: float = 1.0) -> CheckFn:
    def check() -> HealthCheckResult:
        try:
            import shutil
            usage = shutil.disk_usage(path)
            free_gb = usage.free / (1024 ** 3)
            if free_gb < threshold_gb:
                return HealthCheckResult(
                    name="disk",
                    status=HealthStatus.DEGRADED,
                    detail=f"low_disk_space: {free_gb:.2f}GB free",
                    metadata={"free_gb": free_gb, "total_gb": usage.total / (1024 ** 3)},
                )
            return HealthCheckResult(
                name="disk",
                status=HealthStatus.HEALTHY,
                detail="disk_ok",
                metadata={"free_gb": free_gb, "total_gb": usage.total / (1024 ** 3)},
            )
        except Exception as exc:
            return HealthCheckResult(name="disk", status=HealthStatus.UNHEALTHY, detail=str(exc))
    return check


def create_memory_health_check(threshold_mb: float = 500.0) -> CheckFn:
    def check() -> HealthCheckResult:
        try:
            import psutil
            mem = psutil.virtual_memory()
            available_mb = mem.available / (1024 ** 2)
            if available_mb < threshold_mb:
                return HealthCheckResult(
                    name="memory",
                    status=HealthStatus.DEGRADED,
                    detail=f"low_memory: {available_mb:.0f}MB available",
                    metadata={"available_mb": available_mb, "percent": mem.percent},
                )
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.HEALTHY,
                detail="memory_ok",
                metadata={"available_mb": available_mb, "percent": mem.percent},
            )
        except ImportError:
            return HealthCheckResult(name="memory", status=HealthStatus.HEALTHY, detail="psutil_not_available")
        except Exception as exc:
            return HealthCheckResult(name="memory", status=HealthStatus.UNHEALTHY, detail=str(exc))
    return check
