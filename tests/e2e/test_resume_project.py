from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestResumeProjectE2E:
    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Resume Checkpoint",
        )
        pid = proj["project_id"]

        await service.save_video(
            project_uuid=pid, video_id=test_project_data["video_id"],
            title="Resume Test", channel_title="Test",
        )
        await service.save_transcript(
            project_uuid=pid, video_id=test_project_data["video_id"],
            plain_text="Transcript data preserved.", language="en", source="youtube",
        )

        await service.update_project(pid, {
            "status": "failed",
            "error_message": "LLM timeout at analysis stage",
            "pipeline_state": {
                "current_stage": "analysis",
                "completed_stages": ["metadata", "transcript"],
            },
        })

        resumed = await service.update_project(pid, {
            "status": "running",
            "error_message": "",
        })
        assert resumed["status"] == "running"
        assert resumed.get("error_message", "") == ""

        await service.save_analysis(
            project_uuid=pid, video_id=test_project_data["video_id"],
            summary="Analysis after resume.", sentiment="positive",
        )
        await service.update_project(pid, {"status": "completed"})
        final = await service.get_project(pid)
        assert final["status"] == "completed"

    @pytest.mark.asyncio
    async def test_resume_after_failure(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Resume After Failure",
        )
        pid = proj["project_id"]

        await service.save_video(
            project_uuid=pid, video_id=test_project_data["video_id"],
            title="Fail Resume", channel_title="Test",
        )

        await service.update_project(pid, {
            "status": "failed",
            "error_message": "Transcript generation failed",
        })

        resumed = await service.update_project(pid, {
            "status": "running",
            "error_message": "",
        })
        assert resumed["status"] == "running"

        await service.save_transcript(
            project_uuid=pid, video_id=test_project_data["video_id"],
            plain_text="Transcript generated after resume.",
            language="en", source="youtube",
        )
        await service.update_project(pid, {"status": "completed"})
        assert (await service.get_project(pid))["status"] == "completed"

    @pytest.mark.asyncio
    async def test_resume_preserves_previous_work(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Preserve Previous Work",
        )
        pid = proj["project_id"]

        await service.save_video(
            project_uuid=pid, video_id=test_project_data["video_id"],
            title="Preserved Video", channel_title="Test",
        )

        await service.save_transcript(
            project_uuid=pid, video_id=test_project_data["video_id"],
            plain_text="Original transcript preserved.",
            language="en", source="youtube",
        )

        await service.update_project(pid, {
            "status": "failed",
            "error_message": "Analysis failed",
            "pipeline_state": {
                "completed_stages": ["metadata", "transcript"],
                "current_stage": "analysis",
            },
        })

        await service.update_project(pid, {"status": "running", "error_message": ""})

        fetched = await service.get_project(pid)
        assert fetched["status"] == "running"

        await service.save_analysis(
            project_uuid=pid, video_id=test_project_data["video_id"],
            summary="New analysis after resume.", sentiment="positive",
        )
        await service.update_project(pid, {"status": "completed"})
        complete = await service.get_project(pid)
        assert complete["status"] == "completed"

    @pytest.mark.asyncio
    async def test_resume_invalid_project(self, service):
        result = await service.get_project("nonexistent-project-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_resume_completed_project(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Already Completed",
        )
        pid = proj["project_id"]

        await service.update_project(pid, {"status": "completed"})
        final = await service.get_project(pid)
        assert final["status"] == "completed"
