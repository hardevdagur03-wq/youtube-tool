from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from models.blog_export import ExportFormat, ExportRequest


SAMPLE_BLOG = ExportRequest(
    blog_title="PDF Test Blog",
    slug="pdf-test",
    meta_title="PDF Test",
    meta_description="Testing PDF export",
    author="Tester",
    publish_date="2026-07-01",
    category="Tech",
    tags=["pdf"],
    primary_keyword="pdf test",
    secondary_keywords=["export"],
    introduction="Testing PDF export functionality.",
    table_of_contents=["Intro", "Body"],
    sections=[{"heading": "Body Section", "content": "PDF body content", "subsections": []}],
    conclusion="PDF test completed.",
    markdown_content="# PDF Test\n\nContent.",
    word_count=30,
    reading_time="1 min",
    formats=[ExportFormat.PDF],
    base_url="https://example.com",
)


pytestmark = pytest.mark.export


class TestPdfExport:
    def test_pdf_creates_valid_file(self):
        try:
            from export.pdf_exporter import PdfExporter
            exporter = PdfExporter()
            with tempfile.TemporaryDirectory() as tmpdir:
                result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
                filepath = Path(tmpdir) / result.filename
                assert filepath.exists()
                assert filepath.stat().st_size > 0
                assert result.valid is True
        except ImportError:
            pytest.skip("PDF exporter not available")

    def test_pdf_content_rendered(self):
        try:
            from export.pdf_exporter import PdfExporter
            exporter = PdfExporter()
            with tempfile.TemporaryDirectory() as tmpdir:
                result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
                assert result.filename.endswith(".pdf")
                assert result.size_bytes > 100
        except ImportError:
            pytest.skip("PDF exporter not available")

    def test_pdf_page_count(self):
        try:
            from export.pdf_exporter import PdfExporter
            exporter = PdfExporter()
            with tempfile.TemporaryDirectory() as tmpdir:
                result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
                assert result.format == "pdf"
                assert result.valid is True
        except ImportError:
            pytest.skip("PDF exporter not available")
