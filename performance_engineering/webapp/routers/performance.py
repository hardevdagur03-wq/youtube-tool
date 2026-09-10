"""Performance metrics API endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from performance_engineering.monitoring import PerformanceDashboard

router = APIRouter(prefix="/api/perf", tags=["performance"])

_dashboard: PerformanceDashboard | None = None


def init_dashboard(dashboard: PerformanceDashboard) -> None:
    """Initialize the dashboard reference.

    Args:
        dashboard: PerformanceDashboard instance.
    """
    global _dashboard
    _dashboard = dashboard


@router.get("/dashboard")
async def get_dashboard() -> dict:
    """Get the full performance dashboard."""
    if _dashboard is None:
        return {"success": False, "error": "Dashboard not initialized"}
    return {"success": True, "dashboard": _dashboard.get_full_dashboard()}


@router.get("/latency/{endpoint}")
async def get_latency(endpoint: str) -> dict:
    """Get latency percentiles for an endpoint."""
    if _dashboard is None:
        return {"success": False, "error": "Dashboard not initialized"}
    percentiles = _dashboard.get_latency_percentiles(endpoint)
    return {"success": True, "endpoint": endpoint, **percentiles.model_dump()}


@router.get("/latency")
async def get_all_latency() -> dict:
    """Get latency percentiles for all endpoints."""
    if _dashboard is None:
        return {"success": False, "error": "Dashboard not initialized"}
    return {
        "success": True,
        "endpoints": _dashboard.get_all_latency_percentiles(),
    }
