"""Comprehensive tests for the Enterprise Export Engine."""

from __future__ import annotations

import pytest

from services.export.export_provider import (
    CSVExportProvider,
    ExportFormat,
    ExportProvider,
    ExportRequest,
    ExportResult,
    HTMLExportProvider,
    JSONExportProvider,
    MarkdownExportProvider,
    MockExportProvider,
)
from services.export.export_gateway import ExportGateway, ExportJob


GENERATED_BLOG = """# Machine Learning Guide

## Introduction

Machine learning is transforming industries.

## Key Concepts

Supervised learning uses labeled data.

Unsupervised learning finds patterns.

## Applications

Healthcare, finance, and autonomous driving.

## Conclusion

Machine learning continues to evolve.
"""


class TestExportProvider:
    def test_provider_must_have_format_name(self):
        assert MarkdownExportProvider().format_name == "markdown"
        assert HTMLExportProvider().format_name == "html"
        assert JSONExportProvider().format_name == "json"
        assert CSVExportProvider().format_name == "csv"

    def test_markdown_export(self):
        provider = MarkdownExportProvider()
        request = ExportRequest(title="Test", content="# Hello\n\nWorld", format=ExportFormat.MARKDOWN)
        result = provider.export(request)
        assert result.success is True
        assert result.format == "markdown"
        assert "# Hello" in result.content

    def test_markdown_with_metadata(self):
        provider = MarkdownExportProvider()
        request = ExportRequest(
            title="My Post",
            author="John",
            content="Content here",
            include_meta=True,
        )
        result = provider.export(request)
        assert "title: My Post" in result.content
        assert "author: John" in result.content

    def test_markdown_with_toc(self):
        provider = MarkdownExportProvider()
        request = ExportRequest(
            title="Post",
            content="## Section 1\n\nText\n\n## Section 2\n\nMore",
            include_toc=True,
        )
        result = provider.export(request)
        assert "Section 1" in result.content
        assert "Section 2" in result.content

    def test_html_export(self):
        provider = HTMLExportProvider()
        request = ExportRequest(
            title="HTML Post",
            content="## Section\n\nParagraph here.",
            format=ExportFormat.HTML,
        )
        result = provider.export(request)
        assert result.success is True
        assert "<h1>HTML Post</h1>" in result.content
        assert "<h2>Section</h2>" in result.content
        assert "Paragraph" in result.content

    def test_html_escaping(self):
        provider = HTMLExportProvider()
        request = ExportRequest(title="<script>", content="<b>bold</b>")
        result = provider.export(request)
        assert "<script>" not in result.content
        assert "&lt;script&gt;" in result.content

    def test_json_export(self):
        provider = JSONExportProvider()
        request = ExportRequest(
            title="JSON Post",
            content="Content data",
            format=ExportFormat.JSON,
        )
        result = provider.export(request)
        assert result.success is True
        import json
        data = json.loads(result.content)
        assert data["title"] == "JSON Post"
        assert data["content"] == "Content data"

    def test_csv_export(self):
        provider = CSVExportProvider()
        request = ExportRequest(
            title="CSV Export",
            format=ExportFormat.CSV,
            options={
                "headers": ["Name", "Value"],
                "rows": [["one", "1"], ["two", "2"]],
            },
        )
        result = provider.export(request)
        assert result.success is True
        assert "Name,Value" in result.content
        assert "one,1" in result.content

    def test_csv_without_rows(self):
        provider = CSVExportProvider()
        request = ExportRequest(format=ExportFormat.CSV)
        result = provider.export(request)
        assert result.success is True

    def test_mock_provider(self):
        provider = MockExportProvider("test")
        request = ExportRequest(content="test")
        result = provider.export(request)
        assert result.success is True

    def test_mock_provider_failure(self):
        provider = MockExportProvider("test", fail=True)
        request = ExportRequest(content="test")
        result = provider.export(request)
        assert result.success is False
        assert "failed" in result.error

    def test_validation(self):
        md = MarkdownExportProvider()
        assert md.validate("# Valid content") is True
        assert md.validate("") is False
        assert md.validate("   ") is False

    def test_json_validation(self):
        js = JSONExportProvider()
        assert js.validate('{"key":"value"}') is True
        assert js.validate("invalid json") is False

    def test_provider_abstract_cannot_instantiate(self):
        with pytest.raises(TypeError):
            ExportProvider()

    def test_file_size_tracking(self):
        provider = MarkdownExportProvider()
        content = "Hello World"
        request = ExportRequest(content=content, format=ExportFormat.MARKDOWN, include_meta=False)
        result = provider.export(request)
        assert result.file_size_bytes == len(content.encode("utf-8"))


class TestExportGateway:
    def test_register_provider(self):
        gateway = ExportGateway()
        gateway.register_provider("markdown", MarkdownExportProvider())
        assert "markdown" in gateway._providers

    def test_export_single_format(self):
        gateway = ExportGateway()
        gateway.register_provider("markdown", MarkdownExportProvider())
        request = ExportRequest(title="Test", content="# Hello", format=ExportFormat.MARKDOWN)
        result = gateway.export(request)
        assert result.success is True
        assert result.format == "markdown"

    def test_export_unregistered_format(self):
        gateway = ExportGateway()
        request = ExportRequest(content="Test", format=ExportFormat.PDF)
        result = gateway.export(request)
        assert result.success is False
        assert "No provider" in result.error

    def test_export_multi_formats(self):
        gateway = ExportGateway()
        gateway.register_provider("markdown", MarkdownExportProvider())
        gateway.register_provider("html", HTMLExportProvider())
        gateway.register_provider("json", JSONExportProvider())

        request = ExportRequest(title="Multi", content=GENERATED_BLOG)
        job = gateway.export_multi(
            request,
            [ExportFormat.MARKDOWN, ExportFormat.HTML, ExportFormat.JSON],
        )
        assert len(job.results) == 3
        assert all(r.success for r in job.results)
        assert job.status == "completed"

    def test_export_all_formats(self):
        gateway = ExportGateway()
        gateway.register_provider("markdown", MarkdownExportProvider())
        gateway.register_provider("html", HTMLExportProvider())
        gateway.register_provider("json", JSONExportProvider())
        gateway.register_provider("csv", CSVExportProvider())

        request = ExportRequest(title="All", content=GENERATED_BLOG)
        job = gateway.export_all(request)
        assert len(job.results) >= 3

    def test_export_partial_failure(self):
        gateway = ExportGateway()
        gateway.register_provider("good", MarkdownExportProvider())
        gateway.register_provider("bad", MockExportProvider("bad", fail=True))

        request = ExportRequest(title="Partial", content=GENERATED_BLOG)
        job = gateway.export_multi(
            request,
            [ExportFormat.MARKDOWN, ExportFormat.PDF],
        )
        assert job.status == "partial"

    def test_validate(self):
        gateway = ExportGateway()
        gateway.register_provider("markdown", MarkdownExportProvider())
        gateway.register_provider("json", JSONExportProvider())

        results = gateway.validate("# Valid")
        assert results.get("markdown") is True
        assert results.get("json") is False

    def test_job_tracking(self):
        gateway = ExportGateway()
        gateway.register_provider("markdown", MarkdownExportProvider())

        request = ExportRequest(title="Job", content=GENERATED_BLOG)
        job = gateway.export_multi(request, [ExportFormat.MARKDOWN])
        assert job.job_id is not None

        fetched = gateway.get_job(job.job_id)
        assert fetched is not None

    def test_job_not_found(self):
        gateway = ExportGateway()
        assert gateway.get_job("nonexistent") is None

    def test_list_formats(self):
        gateway = ExportGateway()
        gateway.register_provider("markdown", MarkdownExportProvider())
        gateway.register_provider("html", HTMLExportProvider())
        formats = gateway.list_formats()
        assert "markdown" in formats
        assert "html" in formats

    def test_job_duration_tracked(self):
        gateway = ExportGateway()
        gateway.register_provider("markdown", MarkdownExportProvider())
        request = ExportRequest(title="Speed", content=GENERATED_BLOG)
        job = gateway.export_multi(request, [ExportFormat.MARKDOWN])
        assert job.duration_ms >= 0


class TestExportResult:
    def test_default_values(self):
        result = ExportResult()
        assert result.success is False
        assert result.format == ""
        assert result.error == ""

    def test_success_result(self):
        result = ExportResult(
            success=True,
            format="markdown",
            content="# Hello",
            file_size_bytes=8,
        )
        assert result.success is True
        assert result.file_size_bytes == 8


class TestExportRequest:
    def test_default_values(self):
        req = ExportRequest()
        assert req.format == ExportFormat.MARKDOWN
        assert req.title == ""
        assert req.include_meta is True
        assert req.options == {}

    def test_custom_values(self):
        req = ExportRequest(
            title="Custom",
            content="Content",
            format=ExportFormat.HTML,
            include_toc=True,
            include_meta=False,
            options={"header": "Custom Header"},
        )
        assert req.format == ExportFormat.HTML
        assert req.include_toc is True
        assert req.options["header"] == "Custom Header"

    def test_full_blog_export(self):
        md = MarkdownExportProvider()
        req = ExportRequest(
            title="Full Blog",
            content=GENERATED_BLOG,
            format=ExportFormat.MARKDOWN,
            include_toc=True,
            include_meta=True,
        )
        result = md.export(req)
        assert result.success is True
        assert result.file_size_bytes > 100


class TestExportFormat:
    def test_enum_values(self):
        assert ExportFormat.MARKDOWN.value == "markdown"
        assert ExportFormat.HTML.value == "html"
        assert ExportFormat.JSON.value == "json"
        assert ExportFormat.CSV.value == "csv"

    def test_all_formats_available(self):
        assert len(ExportFormat) >= 4
