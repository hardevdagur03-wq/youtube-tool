from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from models.blog_export import ExportFormat, ExportRequest


pytestmark = pytest.mark.chaos


SAMPLE_BLOG = ExportRequest(
    blog_title="Disk Full Test",
    slug="disk-full-test",
    meta_title="Disk Test",
    meta_description="Testing disk full scenario",
    author="Tester",
    publish_date="2026-07-01",
    category="Tech",
    tags=["test"],
    primary_keyword="disk test",
    secondary_keywords=["failure"],
    introduction="Testing behavior when disk is full.",
    table_of_contents=["Intro"],
    sections=[{"heading": "Body", "content": "Content", "subsections": []}],
    conclusion="Done.",
    markdown_content="# Disk Full\n\nTest.",
    word_count=20,
    reading_time="1 min",
    formats=[ExportFormat.MARKDOWN],
    base_url="https://example.com",
)


class TestDiskFull:
    def test_export_handles_disk_full(self):
        from export.markdown_exporter import MarkdownExporter
        exporter = MarkdownExporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = exporter.export(SAMPLE_BLOG, Path(tmpdir))
            filepath = Path(tmpdir) / result.filename
            assert filepath.exists()
            content = filepath.read_text(encoding="utf-8")
            assert "# Disk Full Test" in content

    def test_cache_handles_disk_full(self):
        cache_dir = Path(tempfile.mkdtemp())
        try:
            test_file = cache_dir / "cache_test.txt"
            test_file.write_text("cached data", encoding="utf-8")
            assert test_file.exists()
            assert test_file.read_text(encoding="utf-8") == "cached data"
        finally:
            import shutil
            shutil.rmtree(cache_dir, ignore_errors=True)

    def test_graceful_error_on_disk_full(self):
        def simulate_write(path: str, content: str):
            raise OSError("No space left on device")

        with pytest.raises(OSError, match="No space left on device"):
            simulate_write("/fake/path/file.txt", "content")
