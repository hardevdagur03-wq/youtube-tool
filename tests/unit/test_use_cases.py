"""Tests for the Application Layer use cases."""

from __future__ import annotations

import pytest

from application.use_cases.base import Command, Query, Result, UseCase
from application.use_cases.video import (
    CreateVideoCommand,
    CreateVideoUseCase,
    GetVideoQuery,
    GetVideoQueryHandler,
    ListVideosQuery,
    ListVideosQueryHandler,
)
from domain.entities import Video
from domain.value_objects import VideoId
from infrastructure.repositories.memory_repos import InMemoryUnitOfWork


class TestCreateVideoUseCase:
    @pytest.mark.asyncio
    async def test_create_video(self):
        uow = InMemoryUnitOfWork()
        use_case = CreateVideoUseCase(uow)

        command = CreateVideoCommand(video_id="dQw4w9WgXcQ", url="https://youtube.com/watch?v=dQw4w9WgXcQ")
        result = await use_case.execute(command)

        assert result.success is True
        assert result.data is not None
        assert result.data.video_id == VideoId("dQw4w9WgXcQ")

    @pytest.mark.asyncio
    async def test_create_duplicate_video_returns_existing(self):
        uow = InMemoryUnitOfWork()
        use_case = CreateVideoUseCase(uow)

        cmd1 = CreateVideoCommand(video_id="dQw4w9WgXcQ")
        result1 = await use_case.execute(cmd1)

        cmd2 = CreateVideoCommand(video_id="dQw4w9WgXcQ")
        result2 = await use_case.execute(cmd2)

        assert result1.data.id == result2.data.id

    @pytest.mark.asyncio
    async def test_invalid_video_id(self):
        uow = InMemoryUnitOfWork()
        use_case = CreateVideoUseCase(uow)

        command = CreateVideoCommand(video_id="invalid")
        result = await use_case.execute(command)

        assert result.success is False
        assert result.error_code == "INVALID_VIDEO_ID"


class TestGetVideoQueryHandler:
    @pytest.mark.asyncio
    async def test_get_existing_video(self):
        uow = InMemoryUnitOfWork()
        video = Video(video_id=VideoId("dQw4w9WgXcQ"))
        await uow.videos.save(video)

        handler = GetVideoQueryHandler(uow)
        result = await handler.handle(GetVideoQuery(video_id="dQw4w9WgXcQ"))

        assert result.success is True
        assert result.data.video_id == VideoId("dQw4w9WgXcQ")

    @pytest.mark.asyncio
    async def test_get_nonexistent_video(self):
        uow = InMemoryUnitOfWork()
        handler = GetVideoQueryHandler(uow)

        result = await handler.handle(GetVideoQuery(video_id="dQw4w9WgXcQ"))

        assert result.success is False
        assert result.error_code == "NOT_FOUND"


class TestListVideosQueryHandler:
    @pytest.mark.asyncio
    async def test_list_videos(self):
        uow = InMemoryUnitOfWork()
        for i in range(5):
            video = Video(video_id=VideoId(f"dQw4w9Wg{i:03o}"))
            await uow.videos.save(video)

        handler = ListVideosQueryHandler(uow)
        result = await handler.handle(ListVideosQuery(limit=10))

        assert result.success is True
        assert len(result.data) == 5


class TestCommandAndQueryBase:
    def test_command_base(self):
        cmd = Command(request_id="test-req")
        assert cmd.request_id == "test-req"

    def test_result_success(self):
        result = Result(data={"key": "value"})
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error == ""

    def test_result_failure(self):
        result = Result(success=False, error="Something went wrong", error_code="ERROR")
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.error_code == "ERROR"
