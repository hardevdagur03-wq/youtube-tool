from __future__ import annotations

import json
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable

from observability.config import ObservabilityConfig
from observability.logger import get_logger


class BatchExporter:
    def __init__(self, max_batch_size: int = 100, flush_interval_seconds: float = 10.0):
        self._buffer: deque[dict[str, Any]] = deque(maxlen=10000)
        self._max_batch_size = max_batch_size
        self._flush_interval = flush_interval_seconds
        self._last_flush = time.time()
        self._exporters: list[Callable[[list[dict[str, Any]]], None]] = []
        self._logger = get_logger(__name__)

    def add_exporter(self, exporter_fn: Callable[[list[dict[str, Any]]], None]) -> None:
        self._exporters.append(exporter_fn)

    def emit(self, record: dict[str, Any]) -> None:
        self._buffer.append(record)
        if len(self._buffer) >= self._max_batch_size:
            self.flush()

    def flush(self) -> None:
        if not self._buffer:
            return
        batch = [self._buffer.popleft() for _ in range(min(len(self._buffer), self._max_batch_size))]
        for exporter_fn in self._exporters:
            try:
                exporter_fn(batch)
            except Exception as exc:
                self._logger.error("batch_export_failed", error=str(exc))
        self._last_flush = time.time()

    def periodic_flush(self) -> None:
        if time.time() - self._last_flush >= self._flush_interval:
            self.flush()


class TelemetryExporter:
    def __init__(self, config: ObservabilityConfig):
        self._config = config
        self._logger = get_logger(__name__)
        self._batch_exporter = BatchExporter()

    def get_batch_exporter(self) -> BatchExporter:
        return self._batch_exporter

    def export_log(self, record: dict[str, Any]) -> None:
        self._batch_exporter.emit(record)

    def export_metric(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        record = {
            "type": "metric",
            "name": name,
            "value": value,
            "labels": labels or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._batch_exporter.emit(record)

    def export_span(self, span_data: dict[str, Any]) -> None:
        record = {
            "type": "span",
            **span_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._batch_exporter.emit(record)

    def export_event(self, event_data: dict[str, Any]) -> None:
        record = {
            "type": "event",
            **event_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._batch_exporter.emit(record)

    def file_exporter(self, filepath: str) -> Callable[[list[dict[str, Any]]], None]:
        def _export(batch: list[dict[str, Any]]) -> None:
            try:
                with open(filepath, "a") as f:
                    for record in batch:
                        f.write(json.dumps(record) + "\n")
            except Exception as exc:
                self._logger.error("file_export_failed", path=filepath, error=str(exc))
        return _export

    def console_exporter(self) -> Callable[[list[dict[str, Any]]], None]:
        def _export(batch: list[dict[str, Any]]) -> None:
            for record in batch:
                print(json.dumps(record, default=str))
        return _export

    def http_exporter(self, url: str, headers: dict[str, str] | None = None) -> Callable[[list[dict[str, Any]]], None]:
        def _export(batch: list[dict[str, Any]]) -> None:
            try:
                import httpx
                httpx.post(url, json=batch, headers=headers or {})
            except Exception as exc:
                self._logger.error("http_export_failed", url=url, error=str(exc))
        return _export

    def flush(self) -> None:
        self._batch_exporter.flush()
