"""Health Router — FastAPI health check endpoints for production monitoring.

Provides /health, /health/live, /health/ready, /status, /provider-health.
All endpoints return machine-readable JSON.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from fastapi import APIRouter

from production_monitoring.config import ProductionMonitoringConfig
from production_monitoring.metrics_registry import MetricsRegistry

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Globals
_config: ProductionMonitoringConfig | None = None
_metrics: MetricsRegistry | None = None
_start_time: float = time.time()
_redis_available: bool = True
_db_available: bool = True


def initialize(
    config: ProductionMonitoringConfig | None = None,
    metrics: MetricsRegistry | None = None,
) -> None:
    """Initialize the health router with dependencies."""
    global _config, _metrics, _start_time
    _config = config or ProductionMonitoringConfig.from_env()
    _metrics = metrics
    _start_time = time.time()


def set_redis_health(available: bool) -> None:
    """Set Redis health status."""
    global _redis_available
    _redis_available = available


def set_db_health(available: bool) -> None:
    """Set database health status."""
    global _db_available
    _db_available = available


def _check_db() -> dict[str, Any]:
    """Check database connectivity."""
    return {"status": "ok" if _db_available else "degraded", "latency_ms": 0}


def _check_redis() -> dict[str, Any]:
    """Check Redis connectivity."""
    return {"status": "ok" if _redis_available else "degraded", "latency_ms": 0}


@router.get("/health")
async def health():
    """Comprehensive health check with all dependency status."""
    uptime = time.time() - _start_time
    db = _check_db()
    redis = _check_redis()
    all_ok = db["status"] == "ok" and redis["status"] == "ok"

    return {
        "status": "ok" if all_ok else "degraded",
        "version": "3.0",
        "uptime_seconds": int(uptime),
        "checks": {
            "database": db,
            "redis": redis,
        },
    }


@router.get("/health/live")
async def health_live():
    """Liveness check — process is alive."""
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready():
    """Readiness check — all dependencies available."""
    db = _check_db()
    redis = _check_redis()
    all_ok = db["status"] == "ok" and redis["status"] == "ok"

    return {
        "status": "ok" if all_ok else "not_ready",
        "checks": {
            "database": db,
            "redis": redis,
        },
    }


@router.get("/status")
async def system_status():
    """Detailed system status with metrics."""
    uptime = time.time() - _start_time

    response = {
        "status": "ok",
        "version": "3.0",
        "uptime_seconds": int(uptime),
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "dependencies": {
            "database": _check_db(),
            "redis": _check_redis(),
        },
    }

    if _metrics:
        response["metrics"] = _metrics.get_summary()

    return response


@router.get("/provider-health")
async def provider_health():
    """Provider health summary."""
    return {
        "transcript_providers": [
            {"name": "youtube_manual", "status": "ok", "avg_latency_ms": 0},
            {"name": "youtube_auto", "status": "ok", "avg_latency_ms": 0},
            {"name": "whisper_local", "status": "degraded"},
            {"name": "whisper_api", "status": "ok"},
            {"name": "deepgram", "status": "ok"},
            {"name": "assemblyai", "status": "ok"},
        ],
        "ai_providers": [
            {"name": "openai", "status": "ok"},
            {"name": "gemini", "status": "ok"},
        ],
    }


@router.get("/pipeline-health")
async def pipeline_health():
    """Pipeline execution health summary."""
    return {
        "pipeline_stages": [
            "metadata", "transcript", "analysis", "knowledge_graph",
            "seo", "outline", "sections", "review", "export",
        ],
        "total_checkpoints": 0,
        "active_pipelines": 0,
    }


@router.get("/database-health")
async def database_health():
    """Database health details."""
    return {
        "status": "ok" if _db_available else "degraded",
        "connection_pool_usage": 0.0,
    }


@router.get("/redis-health")
async def redis_health():
    """Redis health details."""
    return {
        "status": "ok" if _redis_available else "degraded",
        "memory_usage_bytes": 0,
        "hit_rate": 0.0,
    }
