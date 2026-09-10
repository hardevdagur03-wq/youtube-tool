from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestDeleteProjectE2E:
    @pytest.mark.asyncio
    async def test_delete_project(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="To Delete",
        )
        pid = proj["project_id"]

        assert await service.get_project(pid) is not None

        deleted = await service.delete_project(pid, permanent=False)
        assert deleted is True

        fetched = await service.get_project(pid)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_then_recreate(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id="recreate-video",
            name="Recreate Test",
        )
        pid = proj["project_id"]

        await service.delete_project(pid, permanent=False)
        assert await service.get_project(pid) is None

        proj2 = await service.create_project(
            url=test_project_data["url"],
            video_id="recreate-video",
            name="Recreated Project",
        )
        assert proj2 is not None
        assert proj2["video_id"] == "recreate-video"

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, service):
        result = await service.delete_project("nonexistent-id", permanent=False)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_cleans_up_artifacts(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id="cleanup-artifacts",
            name="Cleanup Test",
        )
        pid = proj["project_id"]

        await service.save_video(
            project_uuid=pid, video_id="cleanup-artifacts",
            title="Cleanup Video", channel_title="Test",
        )
        await service.save_transcript(
            project_uuid=pid, video_id="cleanup-artifacts",
            plain_text="Cleanup transcript.", language="en", source="youtube",
        )
        await service.save_export(
            project_uuid=pid, export_format="markdown",
            filename="cleanup.md", checksum="cln123",
        )

        await service.delete_project(pid, permanent=True)
        assert await service.get_project(pid) is None
