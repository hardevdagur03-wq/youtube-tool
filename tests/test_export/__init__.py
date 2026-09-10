"""Tests for Phase 10 — Export Engine models."""

from __future__ import annotations
from models.blog_export import (
    ExportFormat, ExportFile, ExportRequest, ExportResult, DownloadToken,
)


class TestExportModels:
    def test_export_format_values(self):
        assert ExportFormat.MARKDOWN.value == "markdown"
        assert ExportFormat.HTML.value == "html"
        assert ExportFormat.DOCX.value == "docx"
        assert ExportFormat.PDF.value == "pdf"

    def test_export_file_defaults(self):
        f = ExportFile(format="markdown", filename="test.md")
        assert f.format == "markdown"
        assert f.size_bytes == 0
        assert f.valid is True

    def test_export_file_full(self):
        f = ExportFile(
            format="html",
            filename="test.html",
            size_bytes=65536,
            size_display="64 KB",
            download_url="/downloads/test.html",
            mime_type="text/html",
        )
        assert f.size_bytes == 65536

    def test_export_request_default_formats(self):
        r = ExportRequest()
        assert len(r.formats) == 4
        assert ExportFormat.MARKDOWN in r.formats

    def test_export_request_custom(self):
        r = ExportRequest(
            blog_title="Test Blog",
            formats=[ExportFormat.MARKDOWN, ExportFormat.HTML],
        )
        assert len(r.formats) == 2
        assert r.blog_title == "Test Blog"

    def test_export_result_defaults(self):
        r = ExportResult()
        assert r.success is True
        assert r.file_count == 0

    def test_export_result_with_files(self):
        files = [
            ExportFile(format="markdown", filename="blog.md", size_bytes=1024, size_display="1 KB"),
            ExportFile(format="html", filename="blog.html", size_bytes=2048, size_display="2 KB"),
        ]
        r = ExportResult(
            export_id="exp_abc123",
            generated_files=files,
            file_count=2,
            total_size_bytes=3072,
            total_size_display="3 KB",
        )
        assert r.export_id == "exp_abc123"
        assert r.file_count == 2

    def test_export_error(self):
        r = ExportResult(success=False, error="Something failed")
        assert r.success is False
        assert r.error == "Something failed"

    def test_download_token(self):
        t = DownloadToken(token="tok_123", filename="blog.pdf", export_id="exp_abc")
        assert t.token == "tok_123"
