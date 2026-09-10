"""Structured Log Pipeline — centralized JSON logging with Loki forwarding.

Wraps Python logging to produce structured JSON. Supports Loki HTTP push,
log buffering, and correlation ID injection.
Never outputs plain text logs.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from production_monitoring.config import ProductionMonitoringConfig
from production_monitoring.constants import LOKI_LABELS

# Global context for correlation IDs
_correlation_ctx: dict[str, str] = {}


def set_correlation_id(correlation_id: str) -> None:
    """Set the global correlation ID for the current request."""
    _correlation_ctx["correlation_id"] = correlation_id


def get_correlation_id() -> str:
    """Get the current correlation ID."""
    return _correlation_ctx.get("correlation_id", "")


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    cid = uuid.uuid4().hex[:16]
    set_correlation_id(cid)
    return cid


class StructuredLogPipeline:
    """Centralized JSON logging with Loki forwarding.

    All logs are emitted as structured JSON. Loki receives batches
    asynchronously via HTTP push.

    Usage::

        logger = StructuredLogPipeline()
        logger.info("User registered", extra={"user_id": "u123"})
    """

    def __init__(self, config: ProductionMonitoringConfig | None = None) -> None:
        self._config = config or ProductionMonitoringConfig.from_env()
        self._buffer: list[dict[str, Any]] = []
        self._buffer_lock = threading.Lock()
        self._flush_interval = self._config.loki_flush_interval
        self._batch_size = self._config.loki_batch_size
        self._loki_enabled = self._config.loki_enabled
        self._loki_url = self._config.loki_push_url
        self._total_logs = 0
        self._total_loki_failures = 0

        # Start background flush thread
        if self._loki_enabled:
            self._flush_thread = threading.Thread(
                target=self._flush_loop, daemon=True,
                name="loki-flush",
            )
            self._flush_thread.start()

    def _format_log(
        self, level: str, message: str, **kwargs: Any,
    ) -> dict[str, Any]:
        """Build a structured log entry."""
        correlation_id = get_correlation_id()
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "service": "yt_blog",
            "environment": os.environ.get("ENVIRONMENT", "development"),
            "message": message,
            "correlation_id": correlation_id,
            "module": kwargs.pop("module", ""),
            "request_id": kwargs.pop("request_id", ""),
            "pipeline_id": kwargs.pop("pipeline_id", ""),
            "job_id": kwargs.pop("job_id", ""),
            "provider": kwargs.pop("provider", ""),
            "stage": kwargs.pop("stage", ""),
            "latency_ms": kwargs.pop("latency_ms", 0),
            "status": kwargs.pop("status", ""),
            "error_code": kwargs.pop("error_code", ""),
            "extra": kwargs,
        }
        return {k: v for k, v in record.items() if v != "" and v != 0}

    def _emit(self, level: str, message: str, **kwargs: Any) -> None:
        """Emit a structured log entry."""
        record = self._format_log(level, message, **kwargs)
        # Always output JSON to stdout
        print(json.dumps(record, default=str), flush=True)
        self._total_logs += 1

        # Buffer for Loki
        if self._loki_enabled:
            with self._buffer_lock:
                self._buffer.append(record)
                if len(self._buffer) >= self._batch_size:
                    self._flush_sync()

    def info(self, message: str, **kwargs: Any) -> None:
        self._emit("info", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._emit("warning", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._emit("error", message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        self._emit("critical", message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        self._emit("debug", message, **kwargs)

    def _flush_sync(self) -> None:
        """Synchronously flush log buffer to Loki."""
        if not self._buffer:
            return
        batch = list(self._buffer)
        self._buffer.clear()

        try:
            import httpx
            streams = []
            for record in batch:
                labels = dict(LOKI_LABELS)
                labels["level"] = record["level"]
                log_line = json.dumps(record, default=str)
                nano_ts = int(
                    datetime.fromisoformat(record["timestamp"]).timestamp() * 1e9
                )
                streams.append({
                    "stream": labels,
                    "values": [[str(nano_ts), log_line]],
                })

            payload = {"streams": streams}
            httpx.post(
                self._loki_url,
                json=payload,
                timeout=5.0,
            )
        except Exception as exc:
            self._total_loki_failures += 1
            # Don't retry — logs are already on stdout
            print(
                json.dumps({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": "ERROR",
                    "message": f"Loki push failed: {exc}",
                    "loki_failures": self._total_loki_failures,
                }),
                flush=True,
            )

    def _flush_loop(self) -> None:
        """Background thread to flush logs periodically."""
        while True:
            time.sleep(self._flush_interval)
            try:
                with self._buffer_lock:
                    self._flush_sync()
            except Exception:
                pass

    def flush(self) -> None:
        """Force flush all buffered logs."""
        with self._buffer_lock:
            self._flush_sync()

    def get_stats(self) -> dict[str, Any]:
        """Get logger statistics."""
        return {
            "total_logs": self._total_logs,
            "loki_failures": self._total_loki_failures,
            "buffer_size": len(self._buffer),
            "loki_enabled": self._loki_enabled,
        }
