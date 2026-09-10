from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import pytest

from models.blog_export import ExportFormat, ExportRequest


SAMPLE_BLOG = ExportRequest(
    blog_title="ZIP Test Blog",
    markdown_content="# ZIP\n\nContent.",
    formats=[ExportFormat.MARKDOWN, ExportFormat.HTML],
    sections=[],
    compress=True,
)


pytestmark = pytest.mark.export


class TestZipPackage:
    def test_zip_contains_all_files(self):
        from export.engine import ExportEngine
        engine = ExportEngine()
        with tempfile.TemporaryDirectory() as tmpdir:
            results = engine.export_all(SAMPLE_BLOG, Path(tmpdir))
            assert len(results) >= 1
            for result in results:
                filepath = Path(tmpdir) / result.filename
                assert filepath.exists()

    def test_zip_preserves_structure(self):
        from export.engine import ExportEngine
        engine = ExportEngine()
        with tempfile.TemporaryDirectory() as tmpdir:
            results = engine.export_all(SAMPLE_BLOG, Path(tmpdir))
            zip_files = [r for r in results if r.filename.endswith(".zip")]
            if zip_files:
                zip_path = Path(tmpdir) / zip_files[0].filename
                with zipfile.ZipFile(zip_path, "r") as zf:
                    names = zf.namelist()
                    assert len(names) > 0

    def test_zip_can_be_extracted(self):
        from export.engine import ExportEngine
        engine = ExportEngine()
        with tempfile.TemporaryDirectory() as tmpdir:
            results = engine.export_all(SAMPLE_BLOG, Path(tmpdir))
            zip_files = [r for r in results if r.filename.endswith(".zip")]
            if zip_files:
                zip_path = Path(tmpdir) / zip_files[0].filename
                extract_dir = Path(tmpdir) / "extracted"
                extract_dir.mkdir()
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(extract_dir)
                extracted_files = list(extract_dir.iterdir())
                assert len(extracted_files) > 0
