"""Export Metrics — tracks export operations by format, duration, failures.

Tracks:
- Export count by format (markdown, HTML, PDF, DOCX, TXT, JSON, ZIP)
- Export duration by format
- Export failure rate by format
- Download count tracking
- File size distribution
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from prometheus_client import Counter, Gauge, Histogram

from observability.logger import get_logger

logger = get_logger(__name__)

PREFIX = "youtube_seo_export"

# Counters
export_started = Counter(f"{PREFIX}_started_total", "Exports started", ["format", "project_id"])
export_completed = Counter(f"{PREFIX}_completed_total", "Exports completed", ["format", "project_id"])
export_failed = Counter(f"{PREFIX}_failed_total", "Exports failed", ["format", "project_id", "error_type"])
export_retried = Counter(f"{PREFIX}_retried_total", "Export retries", ["format"])
download_count = Counter(f"{PREFIX}_downloads_total", "Export downloads", ["format"])

# Histograms
export_duration = Histogram(
    f"{PREFIX}_duration_seconds",
    "Export generation duration",
    ["format"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600),
)
export_file_size_bytes = Histogram(
    f"{PREFIX}_file_size_bytes",
    "Exported file size",
    ["format"],
    buckets=(1024, 5120, 10240, 51200, 102400, 512000, 1048576, 5242880, 10485760),
)

# Gauges
active_exports = Gauge(f"{PREFIX}_active", "Currently active exports", ["format"])
export_success_rate = Gauge(f"{PREFIX}_success_rate", "Export success rate (0-1)", ["format"])
export_throughput = Gauge(f"{PREFIX}_throughput_per_minute", "Exports per minute", ["format"])


@dataclass
class ExportMetricsSnapshot:
    format: str = ""
    total_started: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_downloads: int = 0
    success_rate: float = 1.0
    avg_duration_seconds: float = 0.0
    avg_file_size_bytes: float = 0.0
    active_count: int = 0
    timestamp: str = ""


class ExportMetricsCollector:
    """Tracks export operation metrics across all formats."""

    def record_export_started(self, export_format: str, project_id: str = "") -> None:
        export_started.labels(format=export_format, project_id=project_id or "unknown").inc()
        active_exports.labels(format=export_format).inc()

    def record_export_completed(self, export_format: str, project_id: str = "", duration_ms: int = 0, file_size_bytes: int = 0) -> None:
        export_completed.labels(format=export_format, project_id=project_id or "unknown").inc()
        active_exports.labels(format=export_format).dec()
        if duration_ms > 0:
            export_duration.labels(format=export_format).observe(duration_ms / 1000.0)
        if file_size_bytes > 0:
            export_file_size_bytes.labels(format=export_format).observe(file_size_bytes)

    def record_export_failed(self, export_format: str, project_id: str = "", error_type: str = "") -> None:
        export_failed.labels(format=export_format, project_id=project_id or "unknown", error_type=error_type or "unknown").inc()
        active_exports.labels(format=export_format).dec()

    def record_export_retried(self, export_format: str) -> None:
        export_retried.labels(format=export_format).inc()

    def record_download(self, export_format: str) -> None:
        download_count.labels(format=export_format).inc()

    def update_success_rate(self, export_format: str, rate: float) -> None:
        export_success_rate.labels(format=export_format).set(max(0.0, min(1.0, rate)))

    def update_throughput(self, export_format: str, throughput: float) -> None:
        export_throughput.labels(format=export_format).set(throughput)

    def get_active_export_count(self) -> int:
        samples = list(active_exports.collect())
        total = 0
        for s in samples:
            for sample in s.samples:
                total += int(sample.value)
        return total

    def get_snapshot(self, export_format: str = "") -> ExportMetricsSnapshot:
        return ExportMetricsSnapshot(
            format=export_format or "all",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


_export_metrics: ExportMetricsCollector | None = None


def get_export_metrics() -> ExportMetricsCollector:
    global _export_metrics
    if _export_metrics is None:
        _export_metrics = ExportMetricsCollector()
    return _export_metrics
