from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from models.blog_export import ExportFormat, ExportRequest


SAMPLE_BLOG = ExportRequest(
    blog_title="Markdown Test Blog",
    slug="markdown-test",
    meta_title="MD Test",
    meta_description="Testing markdown export",
    author="Tester",
    publish_date="2026-07-01",
    category="Tech",
    tags=["python", "markdown"],
    primary_keyword="markdown test",
    secondary_keywords=["export"],
    introduction="Testing markdown structure and formatting.",
    table_of_contents=["Intro", "Code", "List", "Table"],
    sections=[
        {
            "heading": "Code Examples",
            "content": "Here is some Python code:",
            "subsections": [{"heading": "Function", "content": "def hello(): pass"}],
        },
        {
            "heading": "List Section",
            "content": "Item 1\nItem 2\nItem 3",
            "subsections": [],
        },
    ],
    conclusion="Markdown test complete.",
    markdown_content=(
        "# Markdown Test Blog\n\n"
        "## Code Examples\n\n"
        "```python\ndef hello():\n    print('Hello')\n```\n\n"
        "## List Section\n\n"
        "- Item 1\n- Item 2\n- Item 3\n\n"
        "| Col1 | Col2 |\n|------|------|\n| A    | B    |\n"
    ),
    word_count=100,
    reading_time="1 min",
    formats=[ExportFormat.MARKDOWN],
    base_url="https://example.com",
)


pytestmark = pytest.mark.export


class TestMarkdownExport:
    def test_markdown_heading_structure(self):
        from export.markdown_exporter import MarkdownExporter
        exporter = MarkdownExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
            content = (Path(tmpdir) / result.filename).read_text(encoding="utf-8")
            assert "# Markdown Test Blog" in content
            assert "## Metadata" in content
            assert "## Code Examples" in content
            assert "## List Section" in content

    def test_markdown_content_preserved(self):
        from export.markdown_exporter import MarkdownExporter
        exporter = MarkdownExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
            content = (Path(tmpdir) / result.filename).read_text(encoding="utf-8")
            assert "Hello" in content
            assert "Item 1" in content
            assert "Col1" in content

    def test_markdown_metadata_included(self):
        from export.markdown_exporter import MarkdownExporter
        exporter = MarkdownExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
            content = (Path(tmpdir) / result.filename).read_text(encoding="utf-8")
            assert "Author" in content or "author" in content
            assert "2026-07-01" in content
            assert "python" in content

    def test_markdown_code_blocks(self):
        from export.markdown_exporter import MarkdownExporter
        exporter = MarkdownExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
            content = (Path(tmpdir) / result.filename).read_text(encoding="utf-8")
            assert "```python" in content
            assert "def hello():" in content
            assert "```" in content

    def test_markdown_lists_and_tables(self):
        from export.markdown_exporter import MarkdownExporter
        exporter = MarkdownExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
            content = (Path(tmpdir) / result.filename).read_text(encoding="utf-8")
            assert "- Item 1" in content or "* Item 1" in content
            assert "|" in content
