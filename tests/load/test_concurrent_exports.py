from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from models.blog_export import ExportFormat, ExportRequest


SAMPLE_BLOG = ExportRequest(
    blog_title="Concurrent Export Test",
    slug="concurrent-export",
    meta_title="Concurrent Test",
    meta_description="Testing concurrent exports",
    author="Tester",
    publish_date="2026-07-01",
    category="Tech",
    tags=["test"],
    primary_keyword="concurrent",
    secondary_keywords=["export"],
    introduction="Testing concurrent export behavior.",
    table_of_contents=["Intro"],
    sections=[{"heading": "Body", "content": "Content", "subsections": []}],
    conclusion="Done.",
    markdown_content="# Concurrent\n\nTest.",
    word_count=50,
    reading_time="1 min",
    formats=[ExportFormat.MARKDOWN],
    base_url="https://example.com",
)


pytestmark = pytest.mark.load


class TestConcurrentExports:
    def test_10_concurrent_exports(self, load_test_config):
        from export.markdown_exporter import MarkdownExporter
        exporter = MarkdownExporter()
        n_exports = 10
        results = []
        with tempfile.TemporaryDirectory() as tmpdir:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=n_exports) as executor:
                futures = [executor.submit(exporter.export, SAMPLE_BLOG, Path(tmpdir)) for _ in range(n_exports)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
        assert len(results) == n_exports
        for r in results:
            assert r.filename is not None
            assert r.valid is True

    def test_50_concurrent_exports(self, load_test_config):
        from export.markdown_exporter import MarkdownExporter
        exporter = MarkdownExporter()
        n_exports = 50
        results = []
        with tempfile.TemporaryDirectory() as tmpdir:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
                futures = [executor.submit(exporter.export, SAMPLE_BLOG, Path(tmpdir)) for _ in range(n_exports)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
        assert len(results) == n_exports
        valid_count = sum(1 for r in results if r.valid)
        assert valid_count >= n_exports * 0.95, (
            f"Only {valid_count}/{n_exports} exports valid"
        )
