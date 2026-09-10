"""CSV export service for transformed video metadata records.

Supports both batch export and incremental streaming export.
Incremental mode writes rows as they arrive, reducing memory pressure
and ensuring partial data survives even if the pipeline is interrupted.
"""

import csv
import logging
from pathlib import Path
from typing import Any, Iterator

from config.settings import settings

logger = logging.getLogger(__name__)

CSV_COLUMNS = [
    "video_id",
    "title",
    "upload_date",
    "views",
    "likes",
    "duration",
    "video_type",
    "video_url",
]

_REQUIRED_FIELDS = {"video_id", "title", "duration", "video_type"}


class CSVExporterError(Exception):
    """Base exception for CSV export errors."""
    pass


class StreamingCSVWriter:
    """Incremental CSV writer that opens a file and streams rows one by one.

    Usage::

        with StreamingCSVWriter(run_dir, "videos.csv") as writer:
            for record in records:
                writer.write_row(record)
        summary = writer.summary()
    """

    def __init__(self, output_dir: Path, filename: str = "videos.csv") -> None:
        self._filepath = output_dir / filename
        self._output_dir = output_dir
        self._file = None
        self._writer = None
        self._row_count = 0
        self._skip_count = 0

    def __enter__(self) -> "StreamingCSVWriter":
        self._output_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._file = open(self._filepath, mode="w", encoding="utf-8", newline="")
            self._writer = csv.DictWriter(self._file, fieldnames=CSV_COLUMNS)
            self._writer.writeheader()
        except OSError as exc:
            raise CSVExporterError(f"Cannot write CSV to {self._filepath}: {exc}") from exc
        return self

    def __exit__(self, *args: Any) -> None:
        if self._file:
            self._file.close()
        log_level = logging.INFO if self._row_count > 0 else logging.WARNING
        logger.log(
            log_level,
            "CSV stream closed: %d rows written, %d skipped → %s",
            self._row_count,
            self._skip_count,
            self._filepath,
        )

    def write_row(self, record: dict[str, Any]) -> bool:
        """Write a single transformed record to the CSV.

        Returns True if written, False if skipped (missing required fields).
        """
        missing = _REQUIRED_FIELDS - set(record.keys())
        if missing:
            vid = record.get("video_id", "unknown")
            logger.warning("Skipping record %s: missing fields %s", vid, missing)
            self._skip_count += 1
            return False

        if not record.get("video_id"):
            logger.warning("Skipping record with empty video_id")
            self._skip_count += 1
            return False

        row = {col: record.get(col, "") for col in CSV_COLUMNS}
        if self._writer:
            self._writer.writerow(row)
        self._row_count += 1
        return True

    @property
    def filepath(self) -> Path:
        return self._filepath

    def summary(self) -> dict[str, Any]:
        """Return export summary after the writer is closed."""
        size = self._filepath.stat().st_size if self._filepath.exists() else 0
        return {
            "filepath": str(self._filepath.resolve()),
            "exported": self._row_count,
            "skipped": self._skip_count,
            "file_size_bytes": size,
            "success": True,
        }


class CSVExporter:
    """Exports transformed video metadata records to a CSV file (batch mode).

    Uses Python's built-in ``csv`` module for proper quoting and escaping.
    Output is UTF-8 encoded.

    For large datasets, prefer ``StreamingCSVWriter`` which writes
    incrementally and consumes less memory.
    """

    def __init__(self, output_dir: Path | str | None = None) -> None:
        self._output_dir = Path(output_dir) if output_dir else settings.output_dir

    def export(
        self,
        records: list[dict[str, Any]] | Iterator[dict[str, Any]],
        filename: str = "videos.csv",
    ) -> dict[str, Any]:
        """Write records to a CSV file.

        Can accept either a list or an iterator/generator for memory-efficient
        processing of large datasets.

        Args:
            records: Transformed video records (list or iterator).
            filename: Output filename (default ``videos.csv``).

        Returns:
            Dict with keys: ``filepath``, ``exported``, ``skipped``,
            ``file_size_bytes``, ``success``.
        """
        self._output_dir.mkdir(parents=True, exist_ok=True)
        filepath = self._output_dir / filename

        try:
            with open(filepath, mode="w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writeheader()
                exported = 0
                skipped = 0
                for record in records:
                    missing = _REQUIRED_FIELDS - set(record.keys())
                    if missing:
                        vid = record.get("video_id", "unknown")
                        logger.warning("Skipping record %s: missing fields %s", vid, missing)
                        skipped += 1
                        continue
                    if not record.get("video_id"):
                        logger.warning("Skipping record with empty video_id")
                        skipped += 1
                        continue
                    row = {col: record.get(col, "") for col in CSV_COLUMNS}
                    writer.writerow(row)
                    exported += 1
        except OSError as exc:
            logger.error("Failed to write CSV: %s", exc)
            raise CSVExporterError(f"Cannot write CSV to {filepath}: {exc}") from exc

        file_size = filepath.stat().st_size
        total_input = exported + skipped
        logger.info("CSV exported: %d rows, %d bytes → %s", exported, file_size, filepath)

        return {
            "filepath": str(filepath.resolve()),
            "total_input": total_input,
            "exported": exported,
            "skipped": skipped,
            "file_size_bytes": file_size,
            "success": True,
        }
