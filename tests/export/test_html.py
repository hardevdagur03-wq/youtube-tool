from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from models.blog_export import ExportFormat, ExportRequest


SAMPLE_BLOG = ExportRequest(
    blog_title="HTML Test Blog",
    slug="html-test",
    meta_title="HTML Test",
    meta_description="Testing HTML export",
    author="Tester",
    publish_date="2026-07-01",
    category="Tech",
    tags=["html"],
    primary_keyword="html test",
    secondary_keywords=["export"],
    introduction="Testing HTML structure.",
    table_of_contents=["Intro"],
    sections=[{"heading": "Body", "content": "HTML content here", "subsections": []}],
    conclusion="Done.",
    markdown_content="# HTML Test\n\nContent.",
    word_count=30,
    reading_time="1 min",
    formats=[ExportFormat.HTML],
    base_url="https://example.com",
)


pytestmark = pytest.mark.export


class TestHtmlExport:
    def test_html_structure_valid(self):
        from export.html_exporter import HTMLExporter
        exporter = HTMLExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
            content = (Path(tmpdir) / result.filename).read_text(encoding="utf-8")
            assert "<!DOCTYPE html>" in content or "<html" in content
            assert "</html>" in content
            assert "<head>" in content
            assert "<body>" in content

    def test_html_styling_included(self):
        from export.html_exporter import HTMLExporter
        exporter = HTMLExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
            content = (Path(tmpdir) / result.filename).read_text(encoding="utf-8")
            assert "style" in content or "class=" in content or "css" in content.lower()

    def test_html_metadata(self):
        from export.html_exporter import HTMLExporter
        exporter = HTMLExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
            content = (Path(tmpdir) / result.filename).read_text(encoding="utf-8")
            assert "<title>" in content or "meta" in content
            assert "HTML Test Blog" in content

    def test_html_accessibility_attributes(self):
        from export.html_exporter import HTMLExporter
        exporter = HTMLExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
            content = (Path(tmpdir) / result.filename).read_text(encoding="utf-8")
            assert "role=" in content or "aria-" in content or "alt=" in content
