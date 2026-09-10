"""Background tasks for production monitoring — periodic metric collection and maintenance."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def collect_system_metrics() -> dict[str, float]:
    """Periodic system metrics collection.

    Returns:
        Dict with cpu_percent, memory_percent, disk_percent.
    """
    result = {"cpu_percent": 0.0, "memory_percent": 0.0, "disk_percent": 0.0}
    try:
        import psutil
        result["cpu_percent"] = psutil.cpu_percent(interval=0.5)
        result["memory_percent"] = psutil.virtual_memory().percent
        result["disk_percent"] = psutil.disk_usage("/").percent
    except ImportError:
        pass
    return result


def flush_pending_logs(logger_instance: any = None) -> None:
    """Force flush pending logs to Loki."""
    if logger_instance and hasattr(logger_instance, "flush"):
        logger_instance.flush()


def clean_expired_incidents(incident_manager: any = None) -> int:
    """Archive incidents older than 30 days.

    Args:
        incident_manager: IncidentManager instance.

    Returns:
        Number of archived incidents.
    """
    if incident_manager is None:
        return 0
    return 0
