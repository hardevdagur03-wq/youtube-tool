"""Tests for Phase 10 — Export Engine."""

from __future__ import annotations
import tempfile
from pathlib import Path

from models.blog_export import ExportRequest, ExportFormat, ExportFile
from export.markdown_exporter import MarkdownExporter
from export.html_exporter import HTMLExporter
from export.engine import ExportEngine
from export.validator import ExportValidator


SAMPLE_BLOG = ExportRequest(
    blog_title="Complete Guide to Python Testing",
    slug="complete-guide-python-testing",
    meta_title="Python Testing Guide — Complete Tutorial",
    meta_description="Learn Python testing with pytest. Unit tests, integration tests, and best practices.",
    author="Test Author",
    publish_date="2026-07-01",
    category="Technology",
    tags=["python", "testing", "pytest"],
    primary_keyword="python testing",
    secondary_keywords=["pytest", "unit tests"],
    introduction="Testing is a critical part of software development. It ensures code quality.",
    table_of_contents=["Introduction", "Getting Started", "Best Practices", "Conclusion"],
    sections=[
        {"heading": "Getting Started", "content": "Pytest is the most popular testing framework for Python.", "subsections": []},
        {"heading": "Best Practices", "content": "Keep tests independent. Use descriptive names.", "subsections": [
            {"heading": "Test Structure", "content": "Arrange, Act, Assert pattern."}
        ]},
    ],
    faq=[{"question": "What is pytest?", "answer": "A Python testing framework."}],
    conclusion="Testing is essential for reliable software.",
    call_to_action="Start testing your Python projects today.",
    references=[{"label": "Pytest Docs", "url": "https://docs.pytest.org"}],
    markdown_content="# Python Testing Guide\n\nTesting is critical.\n\n## Getting Started\n\nPytest is great.\n\n```python\ndef test_example():\n    assert 1 + 1 == 2\n```",
    word_count=250,
    reading_time="2 min",
    formats=[ExportFormat.MARKDOWN, ExportFormat.HTML, ExportFormat.DOCX, ExportFormat.PDF],
    compress=True,
    base_url="https://example.com",
)


class TestMarkdownExporter:
    def test_format_name(self):
        e = MarkdownExporter()
        assert e.format_name() == "markdown"

    def test_file_extension(self):
        e = MarkdownExporter()
        assert e.file_extension() == ".md"

    def test_generates_markdown(self):
        e = MarkdownExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = e.export(SAMPLE_BLOG, Path(tmpdir))
            filepath = Path(tmpdir) / result.filename
            assert filepath.exists()
            assert filepath.stat().st_size > 0
            content = filepath.read_text(encoding="utf-8")
            assert "# Complete Guide to Python Testing" in content
            assert "## Metadata" in content
            assert "## Frequently Asked Questions" in content

    def test_sanitize_filename(self):
        e = MarkdownExporter()
        name = e.sanitize_filename("Hello World! @#$ Test")
        assert name == "hello-world-test"


class TestHTMLExporter:
    def test_format_name(self):
        e = HTMLExporter()
        assert e.format_name() == "html"

    def test_generates_html(self):
        e = HTMLExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = e.export(SAMPLE_BLOG, Path(tmpdir))
            filepath = Path(tmpdir) / result.filename
            assert filepath.exists()
            content = filepath.read_text(encoding="utf-8")
            assert "<!DOCTYPE html>" in content
            assert "<title>" in content
            assert "json+ld" in content or "schema.org" in content
            assert "og:title" in content or "twitter:card" in content


class TestDOCXExporter:
    def test_format_name(self):
        from export.docx_exporter import DOCXExporter
        e = DOCXExporter()
        assert e.format_name() == "docx"

    def test_generates_docx(self):
        from export.docx_exporter import DOCXExporter
        e = DOCXExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = e.export(SAMPLE_BLOG, Path(tmpdir))
            filepath = Path(tmpdir) / result.filename
            assert filepath.exists()
            assert filepath.stat().st_size > 0


class TestPDFExporter:
    def test_format_name(self):
        from export.pdf_exporter import PDFExporter
        e = PDFExporter()
        assert e.format_name() == "pdf"

    def test_generates_pdf(self):
        from export.pdf_exporter import PDFExporter
        e = PDFExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = e.export(SAMPLE_BLOG, Path(tmpdir))
            filepath = Path(tmpdir) / result.filename
            assert filepath.exists()
            assert filepath.stat().st_size > 100
            content = filepath.read_bytes()
            assert content.startswith(b'%PDF')


class TestExportEngine:
    def test_engine_initialization(self):
        engine = ExportEngine()
        assert "markdown" in engine._exporters
        assert "html" in engine._exporters
        assert "docx" in engine._exporters
        assert "pdf" in engine._exporters

    def test_export_all_formats(self):
        engine = ExportEngine()
        result = engine.export(SAMPLE_BLOG)
        assert result.success is True
        assert result.file_count == 4
        assert result.execution_time_ms > 0

    def test_export_single_format(self):
        req = ExportRequest(
            blog_title="Test",
            markdown_content="# Test",
            formats=[ExportFormat.MARKDOWN],
        )
        engine = ExportEngine()
        result = engine.export(req)
        assert result.file_count == 1

    def test_export_has_zip(self):
        engine = ExportEngine()
        result = engine.export(SAMPLE_BLOG)
        assert result.zip_download is not None


class TestExportValidator:
    def test_validate_missing_file(self):
        v = ExportValidator()
        ef = ExportFile(format="markdown", filename="test.md")
        result = v.validate(Path("/nonexistent/file.md"), ef)
        assert result.valid is False

    def test_validate_markdown(self):
        v = ExportValidator()
        ef = ExportFile(format="markdown", filename="test.md")
        with tempfile.NamedTemporaryFile(suffix='.md', mode='w', delete=False) as f:
            f.write("# Test Heading\n\nThis is some longer content to pass the size check.")
            f.flush()
            result = v.validate(Path(f.name), ef)
        assert result.valid is True

    def test_validate_html(self):
        v = ExportValidator()
        ef = ExportFile(format="html", filename="test.html")
        with tempfile.NamedTemporaryFile(suffix='.html', mode='w', delete=False) as f:
            f.write("<!DOCTYPE html><html><head><title>Test</title><meta name=\"description\" content=\"Test\"></head><body></body></html>")
            f.flush()
            result = v.validate(Path(f.name), ef)
        assert result.valid is True

    def test_validate_pdf(self):
        v = ExportValidator()
        ef = ExportFile(format="pdf", filename="test.pdf")
        with tempfile.NamedTemporaryFile(suffix='.pdf', mode='wb', delete=False) as f:
            f.write(('%PDF-1.4\n' + 'Some content here that is longer. ' * 30 + '\n%%EOF').encode())
            f.flush()
            result = v.validate(Path(f.name), ef)
            assert result.valid is True

    def test_validate_empty_file(self):
        v = ExportValidator()
        ef = ExportFile(format="markdown", filename="test.md")
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'')
            f.flush()
            result = v.validate(Path(f.name), ef)
            assert result.valid is False
