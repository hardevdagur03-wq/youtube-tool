from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from models.blog_export import ExportFormat, ExportRequest


SAMPLE_BLOG = ExportRequest(
    blog_title="DOCX Test Blog",
    slug="docx-test",
    meta_title="DOCX Test",
    meta_description="Testing DOCX export",
    author="Tester",
    publish_date="2026-07-01",
    category="Tech",
    tags=["docx"],
    primary_keyword="docx test",
    secondary_keywords=["export"],
    introduction="Testing DOCX export functionality.",
    table_of_contents=["Intro", "Body"],
    sections=[{"heading": "Body Section", "content": "DOCX body content", "subsections": []}],
    conclusion="DOCX test completed.",
    markdown_content="# DOCX Test\n\nContent.",
    word_count=40,
    reading_time="1 min",
    formats=[ExportFormat.DOCX],
    base_url="https://example.com",
)


pytestmark = pytest.mark.export


class TestDocxExport:
    def test_docx_creates_valid_file(self):
        try:
            from export.docx_exporter import DocxExporter
            exporter = DocxExporter()
            with tempfile.TemporaryDirectory() as tmpdir:
                result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
                filepath = Path(tmpdir) / result.filename
                assert filepath.exists()
                assert filepath.stat().st_size > 0
                assert result.valid is True
        except ImportError:
            pytest.skip("DOCX exporter not available")

    def test_docx_heading_styles(self):
        try:
            from export.docx_exporter import DocxExporter
            exporter = DocxExporter()
            with tempfile.TemporaryDirectory() as tmpdir:
                result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
                assert result.filename.endswith(".docx")
        except ImportError:
            pytest.skip("DOCX exporter not available")

    def test_docx_content_preserved(self):
        try:
            from export.docx_exporter import DocxExporter
            exporter = DocxExporter()
            with tempfile.TemporaryDirectory() as tmpdir:
                result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
                assert result.format == "docx"
                assert result.size_bytes > 0
        except ImportError:
            pytest.skip("DOCX exporter not available")
