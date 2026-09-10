from __future__ import annotations

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from models.blog_export import ExportFormat, ExportRequest


pytestmark = pytest.mark.performance


SAMPLE_BLOG = ExportRequest(
    blog_title="Performance Test Blog",
    slug="perf-test-blog",
    meta_title="Perf Test",
    meta_description="Testing export performance",
    author="Tester",
    publish_date="2026-07-01",
    category="Tech",
    tags=["test"],
    primary_keyword="perf test",
    secondary_keywords=["performance"],
    introduction="Testing export performance across formats.",
    table_of_contents=["Intro", "Body", "Conclusion"],
    sections=[{"heading": "Body", "content": "Content here.", "subsections": []}],
    conclusion="Done.",
    markdown_content="# Perf\n\nContent.\n\n```python\nx=1\n```",
    word_count=200,
    reading_time="1 min",
    formats=[ExportFormat.MARKDOWN, ExportFormat.HTML],
    base_url="https://example.com",
)


class TestExportTime:
    def test_markdown_export_time(self, performance_config):
        from export.markdown_exporter import MarkdownExporter
        exporter = MarkdownExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            start = time.perf_counter()
            result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
            duration = time.perf_counter() - start
            assert duration < performance_config["export_threshold_s"], (
                f"Markdown export took {duration:.3f}s, threshold {performance_config['export_threshold_s']}s"
            )
            filepath = Path(tmpdir) / result.filename
            assert filepath.exists()
            assert filepath.stat().st_size > 0

    def test_html_export_time(self, performance_config):
        from export.html_exporter import HTMLExporter
        exporter = HTMLExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            start = time.perf_counter()
            result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
            duration = time.perf_counter() - start
            assert duration < performance_config["export_threshold_s"], (
                f"HTML export took {duration:.3f}s, threshold {performance_config['export_threshold_s']}s"
            )
            filepath = Path(tmpdir) / result.filename
            assert filepath.exists()
            assert filepath.stat().st_size > 0

    def test_docx_export_time(self, performance_config):
        from export.docx_exporter import DocxExporter  # noqa: F811
        try:
            exporter = DocxExporter()
            with tempfile.TemporaryDirectory() as tmpdir:
                start = time.perf_counter()
                result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
                duration = time.perf_counter() - start
                assert duration < performance_config["export_threshold_s"] * 2, (
                    f"DOCX export took {duration:.3f}s"
                )
                filepath = Path(tmpdir) / result.filename
                assert filepath.exists()
        except ImportError:
            pytest.skip("DOCX exporter not available")

    def test_pdf_export_time(self, performance_config):
        from export.pdf_exporter import PdfExporter
        try:
            exporter = PdfExporter()
            with tempfile.TemporaryDirectory() as tmpdir:
                start = time.perf_counter()
                result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
                duration = time.perf_counter() - start
                assert duration < performance_config["export_threshold_s"] * 3, (
                    f"PDF export took {duration:.3f}s"
                )
                filepath = Path(tmpdir) / result.filename
                assert filepath.exists()
        except ImportError:
            pytest.skip("PDF exporter not available")
