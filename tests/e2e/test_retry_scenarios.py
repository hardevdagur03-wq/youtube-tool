from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestRetryScenariosE2E:
    @pytest.mark.asyncio
    async def test_retry_failed_stage(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Retry Failed Stage",
        )
        pid = proj["project_id"]

        await service.update_project(pid, {
            "status": "failed",
            "error_message": "Stage failed: API timeout",
            "pipeline_state": {
                "current_stage": "transcript",
                "completed_stages": ["metadata"],
                "failed_stages": [{"stage": "transcript", "error": "API timeout"}],
            },
        })

        await service.update_project(pid, {
            "status": "running",
            "error_message": "",
        })

        await service.save_transcript(
            project_uuid=pid, video_id=test_project_data["video_id"],
            plain_text="Retry attempt transcript.",
            language="en", source="youtube",
        )
        await service.update_project(pid, {"status": "completed"})
        assert (await service.get_project(pid))["status"] == "completed"

    @pytest.mark.asyncio
    async def test_retry_with_different_options(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Retry With Options",
        )
        pid = proj["project_id"]

        await service.update_project(pid, {
            "status": "failed",
            "error_message": "Initial attempt failed",
        })

        await service.update_project(pid, {
            "status": "running",
            "error_message": "",
            "settings": {"tone": "conversational", "target_word_count": 2000},
        })

        await service.update_project(pid, {"status": "completed"})
        final = await service.get_project(pid)
        assert final["status"] == "completed"

    @pytest.mark.asyncio
    async def test_retry_max_attempts(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Max Retries",
        )
        pid = proj["project_id"]

        for attempt in range(3):
            await service.update_project(pid, {
                "status": "failed",
                "error_message": f"Attempt {attempt + 1} failed",
                "pipeline_state": {
                    "current_stage": "analysis",
                    "completed_stages": ["metadata", "transcript"],
                    "retry_count": attempt + 1,
                },
            })
            state = await service.get_project(pid)
            assert state["status"] == "failed"

        await service.update_project(pid, {"status": "running", "error_message": ""})
        await service.save_analysis(
            project_uuid=pid, video_id=test_project_data["video_id"],
            summary="Analysis after multiple retries.", sentiment="positive",
        )
        await service.update_project(pid, {"status": "completed"})
        assert (await service.get_project(pid))["status"] == "completed"

    @pytest.mark.asyncio
    async def test_retry_eventual_success(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Eventual Success",
        )
        pid = proj["project_id"]

        await service.update_project(pid, {
            "status": "failed",
            "error_message": "Temporary error: service unavailable",
        })

        await service.update_project(pid, {
            "status": "failed",
            "error_message": "Temporary error: rate limited",
        })

        await service.update_project(pid, {
            "status": "running",
            "error_message": "",
        })

        await service.save_video(
            project_uuid=pid, video_id=test_project_data["video_id"],
            title="Eventual Success Video", channel_title="Test",
        )
        await service.save_transcript(
            project_uuid=pid, video_id=test_project_data["video_id"],
            plain_text="Eventual success transcript.", language="en", source="youtube",
        )
        await service.update_project(pid, {"status": "completed"})
        assert (await service.get_project(pid))["status"] == "completed"
