"""Export Engine — Phase 10 orchestrator.

Runs all selected exporters, validates output, handles compression.
"""

from __future__ import annotations
import logging
import time
import uuid
import shutil
import zipfile
from pathlib import Path
from typing import Any

from models.blog_export import ExportRequest, ExportResult, ExportFile, ExportFormat
from export.base import BaseExporter
from export.markdown_exporter import MarkdownExporter
from export.html_exporter import HTMLExporter
from export.docx_exporter import DOCXExporter
from export.pdf_exporter import PDFExporter

logger = logging.getLogger(__name__)

EXPORT_DIR = Path(__file__).resolve().parent.parent / "exports"


class ExportEngine:
    """Orchestrates multi-format export generation."""

    def __init__(self, exporters: dict[str, BaseExporter] | None = None):
        self._exporters = exporters or self._default_exporters()
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    def _default_exporters(self) -> dict[str, BaseExporter]:
        return {
            "markdown": MarkdownExporter(),
            "html": HTMLExporter(),
            "docx": DOCXExporter(),
            "pdf": PDFExporter(),
        }

    def export(self, request: ExportRequest) -> ExportResult:
        export_id = f"exp_{uuid.uuid4().hex[:12]}"
        out_dir = EXPORT_DIR / export_id
        out_dir.mkdir(parents=True, exist_ok=True)

        start = time.time()
        logger.info("[ExportEngine] Starting export %s with %d formats",
                     export_id, len(request.formats))

        generated: list[ExportFile] = []
        errors: list[str] = []
        total_size = 0

        for fmt in request.formats:
            exporter = self._exporters.get(fmt.value)
            if not exporter:
                errors.append(f"No exporter for format: {fmt.value}")
                continue

            try:
                result, elapsed = exporter.execute(request, out_dir)
                generated.append(result)
                total_size += result.size_bytes
                logger.info("[ExportEngine] %s done: %s (%s, %.0fms)",
                            fmt.value, result.filename, result.size_display, elapsed)
            except Exception as exc:
                logger.exception("[ExportEngine] %s failed: %s", fmt.value, exc)
                errors.append(f"{fmt.value}: {exc}")

        # Build result
        result = ExportResult(
            export_id=export_id,
            generated_files=generated,
            file_count=len(generated),
            total_size_bytes=total_size,
            total_size_display=self._size_display(total_size),
            execution_time_ms=round((time.time() - start) * 1000, 1),
        )

        # Generate ZIP if requested or multiple files
        if request.compress or len(generated) > 1:
            zip_path = self._create_zip(export_id, out_dir, generated)
            if zip_path:
                result.zip_download = f"/api/export/download/{export_id}.zip"
                total_size += zip_path.stat().st_size

        if errors:
            result.success = len(generated) > 0
            result.error = "; ".join(errors[:3])

        logger.info("[ExportEngine] Export %s complete: %d files, %.1fms",
                    export_id, len(generated), result.execution_time_ms)
        return result

    def _create_zip(self, export_id: str, out_dir: Path, files: list[ExportFile]) -> Path | None:
        zip_path = EXPORT_DIR / f"{export_id}.zip"
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for f in files:
                    file_path = out_dir / f.filename
                    if file_path.exists():
                        zf.write(file_path, f.filename)
                # Add images if present
                images_dir = out_dir / "images"
                if images_dir.exists():
                    for img in images_dir.iterdir():
                        zf.write(img, f"images/{img.name}")
            logger.info("[ExportEngine] ZIP created: %s", zip_path.name)
            return zip_path
        except Exception as exc:
            logger.exception("[ExportEngine] ZIP creation failed: %s", exc)
            return None

    @staticmethod
    def _size_display(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    @staticmethod
    def cleanup(export_id: str) -> None:
        out_dir = EXPORT_DIR / export_id
        zip_path = EXPORT_DIR / f"{export_id}.zip"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        if zip_path.exists():
            zip_path.unlink()
        logger.info("[ExportEngine] Cleaned up %s", export_id)
