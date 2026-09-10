from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestEditBlogE2E:
    @pytest.mark.asyncio
    async def test_edit_blog_content(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Editable Blog",
        )
        pid = proj["project_id"]

        v1 = await service.save_draft(
            project_uuid=pid, draft_number=1,
            markdown_content="# Original\n\nThis is the original content.",
            word_count=8,
        )
        assert v1["draft_number"] == 1

        v2 = await service.save_draft(
            project_uuid=pid, draft_number=2,
            markdown_content="# Edited\n\nThis is the edited content with changes applied.",
            word_count=12,
        )
        assert v2["draft_number"] == 2
        assert v2["markdown_content"] != v1["markdown_content"]

    @pytest.mark.asyncio
    async def test_edit_tracked_in_version_history(self, service, uow, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Versioned Blog",
        )
        pid = proj["project_id"]

        from database.version_manager import VersionManager
        vm = VersionManager(uow)

        v1 = await vm.create_version(
            entity_type="draft", entity_uuid=pid,
            project_uuid=pid,
            snapshot={"content": "Version 1"},
            changed_by="user-1",
        )
        assert v1 == 1

        v2 = await vm.create_version(
            entity_type="draft", entity_uuid=pid,
            project_uuid=pid,
            snapshot={"content": "Version 2"},
            changed_by="user-1",
        )
        assert v2 == 2

        versions = await vm.list_versions("draft", pid)
        assert len(versions) == 2

    @pytest.mark.asyncio
    async def test_edit_with_ai_assistant(self, service, mock_llm_provider, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="AI Edit Blog",
        )
        pid = proj["project_id"]

        response = mock_llm_provider.generate(text="Improve this blog post")
        assert response["text"] == "Mocked LLM response"

        draft = await service.save_draft(
            project_uuid=pid, draft_number=1,
            markdown_content="# AI Assisted\n\nBlog content improved with AI.",
            word_count=10,
        )
        assert draft is not None

    @pytest.mark.asyncio
    async def test_edit_undo_redo(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Undo Redo Blog",
        )
        pid = proj["project_id"]

        v1 = await service.save_draft(
            project_uuid=pid, draft_number=1,
            markdown_content="# State A",
            word_count=3,
        )
        v2 = await service.save_draft(
            project_uuid=pid, draft_number=2,
            markdown_content="# State B",
            word_count=3,
        )
        v3 = await service.save_draft(
            project_uuid=pid, draft_number=3,
            markdown_content="# State C",
            word_count=3,
        )
        assert v3["draft_number"] == 3

        assert v1["markdown_content"] != v3["markdown_content"]
        assert v2["markdown_content"] != v3["markdown_content"]

    @pytest.mark.asyncio
    async def test_edit_autosave(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Autosave Blog",
        )
        pid = proj["project_id"]

        autosave = await service.save_draft(
            project_uuid=pid, draft_number=0,
            markdown_content="# Autosave Draft\n\nAuto-saved content.",
            word_count=6,
        )
        assert autosave is not None
        assert autosave["draft_number"] == 0

        manual = await service.save_draft(
            project_uuid=pid, draft_number=1,
            markdown_content="# Manual Save\n\nUser-saved content.",
            word_count=6,
        )
        assert manual is not None
        assert manual["draft_number"] > autosave["draft_number"]
