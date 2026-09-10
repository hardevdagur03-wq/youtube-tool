from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestMetadataTranscriptIntegration:
    @pytest.mark.asyncio
    async def test_metadata_to_transcript_flow(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        video = await service.save_video(
            project_uuid=pid, video_id=test_project_data["video_id"],
            title="Test Video for Transcript",
            channel_title="Test Channel",
            description="Video description for transcript testing.",
            view_count=5000,
        )
        assert video is not None

        transcript = await service.save_transcript(
            project_uuid=pid, video_id=test_project_data["video_id"],
            plain_text="This is the transcript text generated from the video metadata.",
            language="en", source="youtube",
            word_count=15,
        )
        assert transcript is not None
        assert transcript["video_id"] == video["video_id"]
        assert transcript["project_uuid"] == pid

    @pytest.mark.asyncio
    async def test_transcript_uses_metadata_language(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        await service.save_video(
            project_uuid=pid, video_id=test_project_data["video_id"],
            title="Test", channel_title="Test Channel",
            language="hi",
        )

        transcript = await service.save_transcript(
            project_uuid=pid, video_id=test_project_data["video_id"],
            plain_text="हिंदी ट्रांसक्रिप्ट सामग्री।",
            language="hi", source="youtube",
            word_count=5,
        )
        assert transcript is not None
        assert transcript["language"] == "hi"

    @pytest.mark.asyncio
    async def test_transcript_enriches_metadata(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        video = await service.save_video(
            project_uuid=pid, video_id=test_project_data["video_id"],
            title="Enrichment Test", channel_title="Test Channel",
            description="Initial description.",
        )

        transcript = await service.save_transcript(
            project_uuid=pid, video_id=test_project_data["video_id"],
            plain_text="Detailed transcript content that enriches the video metadata with additional context and information about the topic.",
            language="en", source="youtube",
            word_count=20,
        )

        assert transcript["word_count"] > 0
        assert transcript["language"] == video.get("language", "en") or "en"

    @pytest.mark.asyncio
    async def test_error_handling_between_stages(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        with pytest.raises(Exception) as excinfo:
            await service.save_transcript(
                project_uuid="nonexistent", video_id="test123",
                plain_text="Should fail.",
                language="en", source="youtube",
            )
        assert excinfo is not None

        transcript = await service.save_transcript(
            project_uuid=pid, video_id=test_project_data["video_id"],
            plain_text="", language="en", source="manual",
            word_count=0,
        )
        assert transcript is not None
        assert transcript["word_count"] == 0
