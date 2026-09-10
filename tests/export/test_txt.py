from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from models.blog_export import ExportFormat, ExportRequest


SAMPLE_BLOG = ExportRequest(
    blog_title="TXT Test Blog",
    markdown_content="# TXT Test\n\nPlain text content.\n\nLine 2.",
    formats=[ExportFormat.MARKDOWN],
    sections=[],
)


pytestmark = pytest.mark.export


class TestTxtExport:
    def test_txt_export(self):
        from export.markdown_exporter import MarkdownExporter
        exporter = MarkdownExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
            content = (Path(tmpdir) / result.filename).read_text(encoding="utf-8")
            assert "TXT Test Blog" in content
            assert len(content) > 0

    def test_txt_encoding(self):
        from export.markdown_exporter import MarkdownExporter
        exporter = MarkdownExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
            content = (Path(tmpdir) / result.filename).read_bytes()
            assert content[:3] != b'\xef\xbb\xbf'
            text = content.decode("utf-8")
            assert isinstance(text, str)
