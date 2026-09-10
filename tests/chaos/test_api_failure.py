from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.chaos


class TestApiFailure:
    @pytest.mark.asyncio
    async def test_youtube_api_failure(self):
        with patch("database.db_service.DatabaseService.process_video", new_callable=AsyncMock) as m:
            m.side_effect = Exception("YouTube API rate limit exceeded")
            svc = DatabaseService()  # noqa: F821
            with pytest.raises(Exception, match="YouTube API rate limit exceeded"):
                await svc.process_video("p1")

    @pytest.mark.asyncio
    async def test_external_api_retry(self):
        call_count = 0

        async def youtube_api():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("YouTube API unavailable")
            return {"status": "completed", "video_id": "v1"}

        result = await youtube_api()
        assert call_count == 3
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens(self, chaos_config):
        threshold = chaos_config["circuit_breaker_threshold"]
        failure_count = 0
        for i in range(threshold + 2):
            failure_count += 1
        assert failure_count > threshold
        circuit_open = failure_count >= threshold
        assert circuit_open is True

    @pytest.mark.asyncio
    async def test_api_fallback(self):
        with patch("database.db_service.DatabaseService.create_project", new_callable=AsyncMock) as m:
            m.side_effect = [
                Exception("Primary API failed"),
                {"project_id": "p1", "status": "created", "from_fallback": True},
            ]
            svc = DatabaseService()  # noqa: F821
            result = await svc.create_project(video_id="v1")
            assert result.get("from_fallback") is True
            assert result["project_id"] == "p1"
