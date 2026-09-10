"""Base exporter interface."""

from __future__ import annotations
from abc import ABC, abstractmethod
import logging
import time
from pathlib import Path

from models.blog_export import ExportRequest, ExportFile

logger = logging.getLogger(__name__)


class BaseExporter(ABC):
    """Abstract base for all format exporters."""

    @abstractmethod
    def format_name(self) -> str:
        """Return format identifier (e.g. 'markdown', 'html')."""
        pass

    @abstractmethod
    def file_extension(self) -> str:
        """Return file extension (e.g. '.md', '.html')."""
        pass

    @abstractmethod
    def mime_type(self) -> str:
        """Return MIME type for the format."""
        pass

    @abstractmethod
    def export(self, request: ExportRequest, output_dir: Path) -> ExportFile:
        """Generate the export file in the output directory.

        Args:
            request: Export request with all blog data.
            output_dir: Directory to write the output file.

        Returns:
            ExportFile with metadata about the generated file.
        """
        pass

    def execute(self, request: ExportRequest, output_dir: Path) -> tuple[ExportFile, float]:
        """Execute with timing and logging."""
        start = time.time()
        try:
            result = self.export(request, output_dir)
            elapsed = round((time.time() - start) * 1000, 1)
            logger.info("[Export] %s generated in %.1fms (%s, %s)",
                        self.format_name(), elapsed, result.filename, result.size_display)
            return result, elapsed
        except Exception as exc:
            elapsed = round((time.time() - start) * 1000, 1)
            logger.exception("[Export] %s failed after %.1fms: %s",
                             self.format_name(), elapsed, exc)
            raise

    def sanitize_filename(self, title: str) -> str:
        """Convert blog title to safe filename."""
        import re
        name = title.lower().strip()
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'[\s_]+', '-', name)
        name = re.sub(r'-+', '-', name)
        return name.strip('-')[:80] or 'blog-export'

    def _size_display(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
