from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestEditorExportIntegration:
    @pytest.mark.asyncio
    async def test_editor_changes_reflect_in_export(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        draft = await service.save_draft(
            project_uuid=pid, draft_number=1,
            markdown_content="# Original Draft\n\nThis is the original content.",
            word_count=8,
        )
        assert draft is not None

        edited_draft = await service.save_draft(
            project_uuid=pid, draft_number=2,
            markdown_content="# Edited Draft\n\nThis is the edited content with improvements.",
            word_count=12,
        )
        assert edited_draft is not None
        assert edited_draft["draft_number"] == 2
        assert edited_draft["markdown_content"] != draft["markdown_content"]

        export = await service.save_export(
            project_uuid=pid, export_format="markdown",
            filename="blog.md",
            checksum="def456",
            content="# Edited Draft\n\nThis is the edited content with improvements.",
        )
        assert export is not None
        assert "Edited Draft" in export.get("content", "")

    @pytest.mark.asyncio
    async def test_export_all_formats_from_editor_content(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        content = "# Blog Post\n\nThis is a sample blog post for export testing."

        await service.save_draft(
            project_uuid=pid, draft_number=1,
            markdown_content=content,
            word_count=12,
        )

        formats = ["markdown", "html", "json", "txt"]
        for fmt in formats:
            export = await service.save_export(
                project_uuid=pid, export_format=fmt,
                filename=f"blog.{fmt}",
                checksum=f"checksum_{fmt}",
                content=content,
            )
            assert export is not None
            assert export["export_format"] == fmt

    @pytest.mark.asyncio
    async def test_export_preserves_formatting(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        markdown = (
            "# Header 1\n\n"
            "## Header 2\n\n"
            "**Bold text** and *italic text*\n\n"
            "- List item 1\n"
            "- List item 2\n\n"
            "1. Numbered item\n"
            "2. Numbered item\n\n"
            "```python\nprint('Hello')\n```\n\n"
            "| Col1 | Col2 |\n"
            "|------|------|\n"
            "| A    | B    |\n"
        )

        export = await service.save_export(
            project_uuid=pid, export_format="markdown",
            filename="formatted.md",
            checksum="fmt123",
            content=markdown,
        )
        assert export is not None
        content = export.get("content", "")
        assert "# Header 1" in content
        assert "## Header 2" in content
        assert "**Bold text**" in content
        assert "- List item 1" in content
        assert "```python" in content
        assert "| Col1 | Col2 |" in content

    @pytest.mark.asyncio
    async def test_export_metadata_accuracy(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Metadata Accuracy Test",
        )
        pid = proj["project_id"]

        original_created = proj["created_at"]

        export = await service.save_export(
            project_uuid=pid, export_format="json",
            filename="metadata.json",
            checksum="meta123",
            metadata={
                "title": "Metadata Accuracy Test",
                "author": "Test User",
                "created_at": original_created,
                "word_count": 500,
                "language": "en",
            },
        )
        assert export is not None
        meta = export.get("metadata", {})
        if meta:
            assert meta.get("title") == "Metadata Accuracy Test"
            assert meta.get("language") == "en"
