"""Status and metrics endpoints for production monitoring."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from production_monitoring.metrics_registry import MetricsRegistry

logger = logging.getLogger(__name__)

router = APIRouter(tags=["metrics"])

_metrics: MetricsRegistry | None = None


def initialize(metrics: MetricsRegistry) -> None:
    """Initialize the metrics router."""
    global _metrics
    _metrics = metrics


@router.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
    if _metrics is None:
        return {"error": "Metrics not initialized"}
    return {"metrics": _metrics.get_summary()}
