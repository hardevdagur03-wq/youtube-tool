from __future__ import annotations

import json
import os
import tempfile

from observability.config import ObservabilityConfig
from observability.telemetry_exporter import TelemetryExporter, BatchExporter


class TestBatchExporter:
    def test_emit_and_flush(self):
        exporter = BatchExporter(max_batch_size=10, flush_interval_seconds=60)
        records = []
        exporter.add_exporter(lambda batch: records.extend(batch))
        exporter.emit({"type": "test", "value": 1})
        exporter.emit({"type": "test", "value": 2})
        exporter.flush()
        assert len(records) == 2

    def test_auto_flush_on_batch_size(self):
        exporter = BatchExporter(max_batch_size=3, flush_interval_seconds=60)
        records = []
        exporter.add_exporter(lambda batch: records.extend(batch))
        exporter.emit({"id": 1})
        exporter.emit({"id": 2})
        assert len(records) == 0
        exporter.emit({"id": 3})
        assert len(records) == 3

    def test_periodic_flush(self):
        exporter = BatchExporter(max_batch_size=100, flush_interval_seconds=0)
        records = []
        exporter.add_exporter(lambda batch: records.extend(batch))
        exporter.emit({"type": "test"})
        exporter.periodic_flush()
        assert len(records) == 1

    def test_exporter_error_handling(self):
        exporter = BatchExporter(max_batch_size=1, flush_interval_seconds=60)

        def failing_exporter(batch):
            raise RuntimeError("export failed")

        exporter.add_exporter(failing_exporter)
        exporter.emit({"type": "test"})  # Should not raise


class TestTelemetryExporter:
    def setup_method(self):
        self.config = ObservabilityConfig()
        self.te = TelemetryExporter(self.config)

    def test_export_log(self):
        self.te.export_log({"type": "log", "level": "info", "message": "test"})

    def test_export_metric(self):
        self.te.export_metric("test_metric", 42.0, {"env": "test"})

    def test_export_span(self):
        self.te.export_span({"name": "test_span", "duration_ms": 100})

    def test_export_event(self):
        self.te.export_event({"name": "test_event", "severity": "info"})

    def test_console_exporter(self):
        exporter = self.te.console_exporter()
        exporter([{"type": "test"}])  # Should not raise

    def test_file_exporter(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            filepath = f.name
        try:
            exporter = self.te.file_exporter(filepath)
            exporter([{"type": "test", "value": 42}])
            with open(filepath) as f:
                line = f.read().strip()
            assert json.loads(line)["value"] == 42
        finally:
            os.unlink(filepath)

    def test_flush(self):
        self.te.flush()
