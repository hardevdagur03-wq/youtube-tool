from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestCreateProjectE2E:
    @pytest.mark.asyncio
    async def test_create_project_with_valid_url(self, service, test_video_url):
        proj = await service.create_project(
            url=test_video_url,
            video_id="dQw4w9WgXcQ",
            name="Test Project",
        )
        assert proj is not None
        assert proj["project_id"] is not None
        assert proj["name"] == "Test Project"
        assert proj["video_id"] == "dQw4w9WgXcQ"
        assert proj["status"] == "created"

    @pytest.mark.asyncio
    async def test_create_project_with_invalid_url(self, service):
        proj = await service.create_project(
            url="invalid-url",
            video_id="unknown",
            name="Invalid URL Project",
        )
        assert proj is not None
        assert proj["project_id"] is not None

    @pytest.mark.asyncio
    async def test_create_project_returns_correct_schema(self, service, test_video_url):
        proj = await service.create_project(
            url=test_video_url,
            video_id="dQw4w9WgXcQ",
            name="Schema Test",
        )
        expected_keys = {"project_id", "name", "video_id", "url", "status", "created_at", "language"}
        assert expected_keys.issubset(set(proj.keys())), f"Missing keys: {expected_keys - set(proj.keys())}"
        assert isinstance(proj["project_id"], str)
        assert isinstance(proj["name"], str)
        assert isinstance(proj["status"], str)

    @pytest.mark.asyncio
    async def test_create_project_persists_to_db(self, service, test_video_url):
        proj = await service.create_project(
            url=test_video_url,
            video_id="persist-test",
            name="Persistence Check",
        )
        pid = proj["project_id"]

        fetched = await service.get_project(pid)
        assert fetched is not None
        assert fetched["project_id"] == pid
        assert fetched["name"] == "Persistence Check"
        assert fetched["video_id"] == "persist-test"

    @pytest.mark.asyncio
    async def test_create_project_duplicate_handling(self, service, test_video_url):
        proj1 = await service.create_project(
            url=test_video_url,
            video_id="dup-video",
            name="Original",
        )

        proj2 = await service.create_project(
            url=test_video_url,
            video_id="dup-video",
            name="Duplicate",
        )

        assert proj1 is not None
        assert proj2 is not None
