"""Worker Health — active/idle/busy tracking, memory/CPU metrics, auto-restart."""

from __future__ import annotations

import logging
import platform
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from background_processing.config import BackgroundProcessingConfig

logger = logging.getLogger(__name__)


class WorkerStatus(Enum):
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    STOPPED = "stopped"


@dataclass
class WorkerHealthSnapshot:
    worker_id: str
    hostname: str
    status: WorkerStatus
    active_tasks: int = 0
    cpu_percent: float = 0.0
    memory_rss_bytes: int = 0
    memory_percent: float = 0.0
    pid: int = 0
    uptime_seconds: float = 0.0
    tasks_processed: int = 0
    last_heartbeat: datetime | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    errors: list[str] = field(default_factory=list)


class HealthMonitor:
    """Monitors worker health and triggers auto-restart when needed.

    Runs a background thread that periodically collects metrics
    from all registered workers and takes corrective action.
    """

    def __init__(
        self,
        config: BackgroundProcessingConfig | None = None,
        restart_callback: Callable[[str], None] | None = None,
        check_interval: float = 15.0,
        max_cpu_percent: float = 90.0,
        max_memory_percent: float = 85.0,
        max_consecutive_failures: int = 3,
    ) -> None:
        self._config = config or BackgroundProcessingConfig.from_env()
        self._restart_callback = restart_callback
        self._check_interval = check_interval
        self._max_cpu = max_cpu_percent
        self._max_mem = max_memory_percent
        self._max_failures = max_consecutive_failures

        self._hostname = socket.gethostname()
        self._snapshots: dict[str, WorkerHealthSnapshot] = {}
        self._consecutive_failures: dict[str, int] = {}
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the health monitoring background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="worker-health-monitor",
        )
        self._thread.start()
        logger.info("Health monitor started (interval=%ss)", self._check_interval)

    def stop(self) -> None:
        """Stop the health monitoring background thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None
        logger.info("Health monitor stopped")

    # ------------------------------------------------------------------
    # Monitoring loop
    # ------------------------------------------------------------------

    def _monitor_loop(self) -> None:
        while self._running:
            try:
                self._check_all()
            except Exception as exc:
                logger.error("Health check error: %s", exc)
            time.sleep(self._check_interval)

    def _check_all(self) -> None:
        import psutil
        with self._lock:
            worker_ids = list(self._snapshots.keys())

        for wid in worker_ids:
            try:
                self._check_worker(wid)
            except Exception as exc:
                logger.warning("Health check failed for %s: %s", wid, exc)
                failures = self._consecutive_failures.get(wid, 0) + 1
                self._consecutive_failures[wid] = failures
                if failures >= self._max_failures:
                    logger.error(
                        "Worker %s exceeded max consecutive failures (%d), triggering restart",
                        wid, failures,
                    )
                    self._trigger_restart(wid)

    def _check_worker(self, worker_id: str) -> None:
        import psutil
        snapshot = self._snapshots.get(worker_id)
        if not snapshot:
            return

        try:
            proc = psutil.Process(snapshot.pid)
            cpu = proc.cpu_percent(interval=0.3)
            mem_info = proc.memory_info()
            mem_percent = proc.memory_percent()
            status = WorkerStatus.ACTIVE

            if cpu > self._max_cpu or mem_percent > self._max_mem:
                status = WorkerStatus.DEGRADED
            if cpu > 95 or mem_percent > 95:
                status = WorkerStatus.UNHEALTHY

            errors: list[str] = []
            if cpu > self._max_cpu:
                errors.append(f"CPU at {cpu:.1f}% (threshold {self._max_cpu}%)")
            if mem_percent > self._max_mem:
                errors.append(f"Memory at {mem_percent:.1f}% (threshold {self._max_mem}%)")

            self._consecutive_failures[worker_id] = 0
            self._snapshots[worker_id] = WorkerHealthSnapshot(
                worker_id=worker_id,
                hostname=self._hostname,
                status=status,
                active_tasks=len(proc.children()),
                cpu_percent=cpu,
                memory_rss_bytes=mem_info.rss,
                memory_percent=mem_percent,
                pid=proc.pid,
                uptime_seconds=time.time() - proc.create_time(),
                tasks_processed=snapshot.tasks_processed,
                last_heartbeat=datetime.now(timezone.utc),
                errors=errors,
            )

            if status in (WorkerStatus.DEGRADED, WorkerStatus.UNHEALTHY):
                logger.warning(
                    "Worker %s is %s: CPU=%s%% MEM=%s%%",
                    worker_id, status.value, f"{cpu:.1f}", f"{mem_percent:.1f}",
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            self._consecutive_failures[worker_id] = (
                self._consecutive_failures.get(worker_id, 0) + 1
            )
            self._snapshots[worker_id] = WorkerHealthSnapshot(
                worker_id=worker_id,
                hostname=self._hostname,
                status=WorkerStatus.STOPPED,
                errors=["Process not found"],
            )

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_worker(
        self,
        worker_id: str,
        pid: int,
    ) -> None:
        """Register a worker for health monitoring."""
        with self._lock:
            self._snapshots[worker_id] = WorkerHealthSnapshot(
                worker_id=worker_id,
                hostname=self._hostname,
                status=WorkerStatus.ACTIVE,
                pid=pid,
            )
            self._consecutive_failures[worker_id] = 0
        logger.info("Worker registered for health monitoring: %s (pid=%d)", worker_id, pid)

    def unregister_worker(self, worker_id: str) -> None:
        """Unregister a worker from health monitoring."""
        with self._lock:
            self._snapshots.pop(worker_id, None)
            self._consecutive_failures.pop(worker_id, None)
        logger.info("Worker unregistered from health monitoring: %s", worker_id)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_health(self, worker_id: str) -> WorkerHealthSnapshot | None:
        with self._lock:
            return self._snapshots.get(worker_id)

    def get_all_health(self) -> list[WorkerHealthSnapshot]:
        with self._lock:
            return list(self._snapshots.values())

    def get_summary(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._snapshots)
            statuses: dict[str, int] = {}
            for s in self._snapshots.values():
                statuses[s.status.value] = statuses.get(s.status.value, 0) + 1
            avg_cpu = (
                sum(s.cpu_percent for s in self._snapshots.values()) / total
                if total > 0 else 0
            )
            avg_mem = (
                sum(s.memory_percent for s in self._snapshots.values()) / total
                if total > 0 else 0
            )
        return {
            "total_workers": total,
            "statuses": statuses,
            "avg_cpu_percent": round(avg_cpu, 1),
            "avg_memory_percent": round(avg_mem, 1),
            "healthy": total > 0 and statuses.get("unhealthy", 0) == 0,
        }

    # ------------------------------------------------------------------
    # Auto-restart
    # ------------------------------------------------------------------

    def _trigger_restart(self, worker_id: str) -> None:
        if self._restart_callback:
            try:
                self._restart_callback(worker_id)
                logger.info("Restart triggered for worker %s", worker_id)
                self._consecutive_failures[worker_id] = 0
            except Exception as exc:
                logger.error("Restart callback failed for %s: %s", worker_id, exc)
