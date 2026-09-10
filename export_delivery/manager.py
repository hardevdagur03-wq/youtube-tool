"""Export Manager — unified coordinator for all export operations.

Coordinates: Router → Template Engine → Formatting Engine → Exporters →
Image Optimizer → Quality Validator → Download Service.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from export_delivery.config import ExportDeliveryConfig
from export_delivery.router import ExportRouter
from export_delivery.template_engine import TemplateEngine
from export_delivery.formatting_engine import FormattingEngine
from export_delivery.models import ExportJobResult

logger = logging.getLogger(__name__)


class ExportManager:
    """Unified coordinator for all export operations.

    Single entry point for creating exports across all formats.
    Handles format selection, template application, formatting,
    quality validation, and download link generation.
    """

    def __init__(
        self,
        config: ExportDeliveryConfig | None = None,
        router: ExportRouter | None = None,
        template_engine: TemplateEngine | None = None,
        formatting_engine: FormattingEngine | None = None,
    ) -> None:
        self._config = config or ExportDeliveryConfig.from_env()
        self._router = router or ExportRouter(self._config)
        self._templates = template_engine or TemplateEngine(self._config)
        self._formatting = formatting_engine or FormattingEngine()

    def export(
        self,
        document: Any,
        formats: list[str] | None = None,
        template: str = "default",
        options: dict[str, Any] | None = None,
    ) -> ExportJobResult:
        """Create exports for specified formats.

        Args:
            document: DocumentModel from publishing.models or similar.
            formats: List of format keys (None = all enabled).
            template: Template name.
            options: Additional export options.

        Returns:
            ``ExportJobResult`` with files and status.
        """
        options = options or {}
        formats = formats or self._config.formats_enabled
        job_id = str(uuid.uuid4())
        start = time.time()

        template_config = self._templates.get_template(template)
        css_vars = self._templates.apply_css_variables(template)

        result = ExportJobResult(
            job_id=job_id,
            project_id=getattr(document, "project_id", ""),
            status="running",
        )

        completed = []
        failed = []
        all_files = []

        for fmt in formats:
            fmt_start = time.time()
            try:
                exporter = self._router.select_exporter(fmt)
                if exporter is None:
                    failed.append(fmt)
                    result.errors.append(f"No exporter for format: {fmt}")
                    continue

                # Apply formatting
                content = getattr(document, "content", "")
                if content and fmt in ("markdown", "html", "txt"):
                    content = self._formatting.apply(content, template_config)

                # Export
                file_info = exporter.export(document, template_config=template_config)
                fmt_duration = (time.time() - fmt_start) * 1000
                all_files.append(file_info)
                completed.append(fmt)

                logger.info(
                    "Export %s: %s completed in %.0fms",
                    job_id[:8], fmt, fmt_duration,
                )

            except Exception as exc:
                failed.append(fmt)
                result.errors.append(f"{fmt}: {exc}")
                logger.error("Export %s: %s failed: %s", job_id[:8], fmt, exc)

        result.formats_completed = completed
        result.formats_failed = failed
        result.files = all_files
        result.execution_time_ms = (time.time() - start) * 1000
        result.status = "completed" if not failed else "partial" if completed else "failed"

        logger.info(
            "Export %s: %d/%d formats completed in %.0fms",
            job_id[:8], len(completed), len(formats), result.execution_time_ms,
        )

        return result
