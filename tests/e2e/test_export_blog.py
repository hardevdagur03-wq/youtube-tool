from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestExportBlogE2E:
    @pytest.mark.asyncio
    async def test_export_markdown(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Export MD",
        )
        pid = proj["project_id"]

        export = await service.save_export(
            project_uuid=pid, export_format="markdown",
            filename="blog.md", checksum="md123",
            content="# Blog\n\nMarkdown content.",
        )
        assert export is not None
        assert export["export_format"] == "markdown"
        assert export["filename"] == "blog.md"

    @pytest.mark.asyncio
    async def test_export_html(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Export HTML",
        )
        pid = proj["project_id"]

        export = await service.save_export(
            project_uuid=pid, export_format="html",
            filename="blog.html", checksum="html123",
            content="<h1>Blog</h1><p>HTML content.</p>",
        )
        assert export is not None
        assert export["export_format"] == "html"

    @pytest.mark.asyncio
    async def test_export_docx(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Export DOCX",
        )
        pid = proj["project_id"]

        export = await service.save_export(
            project_uuid=pid, export_format="docx",
            filename="blog.docx", checksum="docx123",
        )
        assert export is not None
        assert export["export_format"] == "docx"

    @pytest.mark.asyncio
    async def test_export_pdf(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Export PDF",
        )
        pid = proj["project_id"]

        export = await service.save_export(
            project_uuid=pid, export_format="pdf",
            filename="blog.pdf", checksum="pdf123",
        )
        assert export is not None
        assert export["export_format"] == "pdf"

    @pytest.mark.asyncio
    async def test_export_json(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Export JSON",
        )
        pid = proj["project_id"]

        export = await service.save_export(
            project_uuid=pid, export_format="json",
            filename="blog.json", checksum="json123",
            content='{"title": "Blog", "content": "JSON content."}',
        )
        assert export is not None
        assert export["export_format"] == "json"

    @pytest.mark.asyncio
    async def test_export_zip(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Export ZIP",
        )
        pid = proj["project_id"]

        export = await service.save_export(
            project_uuid=pid, export_format="zip",
            filename="blog.zip", checksum="zip123",
        )
        assert export is not None
        assert export["export_format"] == "zip"

    @pytest.mark.asyncio
    async def test_export_all_formats(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Export All",
        )
        pid = proj["project_id"]

        formats = ["markdown", "html", "json", "txt"]
        for fmt in formats:
            export = await service.save_export(
                project_uuid=pid, export_format=fmt,
                filename=f"blog.{fmt}", checksum=f"{fmt}chk",
            )
            assert export is not None

    @pytest.mark.asyncio
    async def test_export_metadata(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Export Metadata",
        )
        pid = proj["project_id"]

        export = await service.save_export(
            project_uuid=pid, export_format="markdown",
            filename="blog.md", checksum="meta123",
            metadata={
                "title": "Export Metadata Test",
                "word_count": 500,
                "language": "en",
                "author": "Test",
            },
        )
        assert export is not None
        meta = export.get("metadata", {})
        if meta:
            assert meta.get("title") == "Export Metadata Test"

    @pytest.mark.asyncio
    async def test_export_invalid_format(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Invalid Format",
        )
        pid = proj["project_id"]

        export = await service.save_export(
            project_uuid=pid, export_format="unknown",
            filename="blog.unknown", checksum="unk123",
        )
        assert export is not None
        assert export["export_format"] == "unknown"
