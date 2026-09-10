"""Worker Manager — lifecycle management, scaling, and health monitoring for workers."""

from __future__ import annotations

import logging
import os
import platform
import signal
import socket
import subprocess
import threading
import time
from datetime import datetime, timezone
from typing import Any

from background_processing.config import BackgroundProcessingConfig
from background_processing.models import WorkerInfo

logger = logging.getLogger(__name__)


class WorkerManager:
    """Manages Celery worker processes — start, stop, monitor, scale.

    Supports:
    - Starting workers with specific queues and concurrency
    - Graceful shutdown
    - Health monitoring
    - Auto-scaling triggers
    - Worker registration with metadata

    This is a control-plane component, typically used by the API server
    or a dedicated management process.
    """

    def __init__(
        self,
        config: BackgroundProcessingConfig | None = None,
    ) -> None:
        self._config = config or BackgroundProcessingConfig.from_env()
        self._workers: dict[str, subprocess.Popen] = {}
        self._hostname = socket.gethostname()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Worker Lifecycle
    # ------------------------------------------------------------------

    def start_worker(
        self,
        worker_id: str = "",
        queues: str = "default,high,low",
        concurrency: int | None = None,
        pool: str = "prefork",
        hostname: str = "",
        loglevel: str = "INFO",
        max_tasks_per_child: int | None = None,
        max_memory_per_child: int | None = None,
        without_heartbeat: bool = False,
        without_mingle: bool = False,
        without_gossip: bool = False,
    ) -> str:
        """Start a Celery worker process.

        Args:
            worker_id: Unique identifier (auto-generated if empty).
            queues: Comma-separated list of queues to consume.
            concurrency: Number of worker processes/threads.
            pool: Pool implementation (prefork, gevent, solo, threads).
            hostname: Celery worker hostname.

        Returns:
            The worker ID.
        """
        wid = worker_id or f"worker-{self._hostname}-{int(time.time())}"
        hostname = hostname or f"{wid}@%h"
        concurrency = concurrency or self._config.worker_concurrency
        max_tasks = max_tasks_per_child or self._config.worker_max_tasks_per_child
        max_mem = max_memory_per_child or self._config.worker_max_memory_per_child

        cmd = [
            "celery",
            "-A", "background_processing.celery_app",
            "worker",
            "--loglevel", loglevel,
            "--concurrency", str(concurrency),
            "--pool", pool,
            "--hostname", hostname,
            "--queues", queues,
            "--max-tasks-per-child", str(max_tasks),
            "--max-memory-per-child", str(max_mem),
        ]

        if without_heartbeat:
            cmd.append("--without-heartbeat")
        if without_mingle:
            cmd.append("--without-mingle")
        if without_gossip:
            cmd.append("--without-gossip")

        with self._lock:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self._workers[wid] = process

        logger.info(
            "Worker started: %s (queues=%s, concurrency=%d, pool=%s, pid=%d)",
            wid, queues, concurrency, pool, process.pid,
        )
        return wid

    def stop_worker(self, worker_id: str, graceful: bool = True) -> bool:
        """Stop a worker by ID.

        Args:
            worker_id: The worker identifier.
            graceful: If True, sends SIGTERM (warm shutdown).
                      If False, sends SIGKILL.

        Returns:
            True if the worker was stopped, False if not found.
        """
        with self._lock:
            process = self._workers.pop(worker_id, None)
        if process is None:
            logger.warning("Worker not found: %s", worker_id)
            return False

        try:
            if graceful:
                process.terminate()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            else:
                process.kill()
                process.wait()
            logger.info("Worker stopped: %s (graceful=%s, pid=%d)", worker_id, graceful, process.pid)
            return True
        except Exception as exc:
            logger.error("Failed to stop worker %s: %s", worker_id, exc)
            return False

    def stop_all(self, graceful: bool = True) -> int:
        """Stop all managed workers.

        Returns:
            Number of workers stopped.
        """
        with self._lock:
            worker_ids = list(self._workers.keys())
        count = 0
        for wid in worker_ids:
            if self.stop_worker(wid, graceful=graceful):
                count += 1
        return count

    def list_workers(self) -> list[WorkerInfo]:
        """List all managed workers with status."""
        workers = []
        with self._lock:
            for wid, process in list(self._workers.items()):
                status = "running" if process.poll() is None else "stopped"
                workers.append(WorkerInfo(
                    worker_id=wid,
                    hostname=self._hostname,
                    status=status,
                ))
        return workers

    def restart_worker(
        self, worker_id: str, queues: str | None = None
    ) -> bool:
        """Restart a worker (stop then start with same config)."""
        info = None
        with self._lock:
            if worker_id in self._workers:
                pass  # keep the entry
        self.stop_worker(worker_id)
        self.start_worker(worker_id=worker_id, queues=queues or "default")
        return True

    # ------------------------------------------------------------------
    # Health & Monitoring
    # ------------------------------------------------------------------

    def get_worker_info(self, worker_id: str) -> WorkerInfo | None:
        """Get detailed information about a specific worker."""
        with self._lock:
            process = self._workers.get(worker_id)
        if process is None:
            return None

        import psutil
        status = "running" if process.poll() is None else "stopped"
        info = WorkerInfo(worker_id=worker_id, hostname=self._hostname, status=status)

        if process.pid and status == "running":
            try:
                proc = psutil.Process(process.pid)
                info.cpu_percent = proc.cpu_percent(interval=0.1)
                mem = proc.memory_info()
                info.memory_rss_bytes = mem.rss
                info.memory_percent = proc.memory_percent()
                info.active_tasks = len(proc.children())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return info

    def get_system_metrics(self) -> dict[str, Any]:
        """Get system-level metrics for all workers."""
        import psutil
        with self._lock:
            total = len(self._workers)
            running = sum(1 for p in self._workers.values() if p.poll() is None)
        return {
            "total_workers": total,
            "running_workers": running,
            "system_cpu_percent": psutil.cpu_percent(interval=0.5),
            "system_memory_percent": psutil.virtual_memory().percent,
            "system_memory_available": psutil.virtual_memory().available,
            "system_disk_usage": psutil.disk_usage("/").percent,
        }

    def health_check(self) -> dict[str, Any]:
        """Comprehensive health check."""
        workers = self.list_workers()
        running_count = sum(1 for w in workers if w.status == "running")
        return {
            "healthy": running_count > 0,
            "workers": {
                "total": len(workers),
                "running": running_count,
            },
            "config": {
                "concurrency": self._config.worker_concurrency,
                "queues": list(self._config.task_queues.keys()),
            },
        }

    def wait_for_workers(
        self, min_workers: int = 1, timeout: int = 30
    ) -> bool:
        """Block until at least min_workers are running."""
        start = time.time()
        while time.time() - start < timeout:
            workers = self.list_workers()
            running = sum(1 for w in workers if w.status == "running")
            if running >= min_workers:
                return True
            time.sleep(1)
        return False
