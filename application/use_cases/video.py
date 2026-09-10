"""Use cases for video operations."""

from __future__ import annotations

from dataclasses import dataclass

from domain.entities import Video
from domain.events import VideoCreated
from domain.repositories import UnitOfWork, VideoRepository
from domain.value_objects import VideoId

from .base import Command, Result, UseCase


@dataclass
class CreateVideoCommand(Command):
    video_id: str = ""
    url: str = ""
    title: str = ""


class CreateVideoUseCase(UseCase[CreateVideoCommand, Result]):
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(self, command: CreateVideoCommand) -> Result:
        try:
            video_id = VideoId(command.video_id)
        except ValueError as e:
            return Result(success=False, error=str(e), error_code="INVALID_VIDEO_ID")

        existing = await self._uow.videos.get_by_video_id(video_id)
        if existing:
            return Result(data=existing)

        video = Video(
            video_id=video_id,
            title=command.title or "",
        )
        video.record_event(VideoCreated(
            video_id=video_id.value,
            url=command.url,
            title=video.title,
        ))
        saved = await self._uow.videos.save(video)
        await self._uow.commit()
        return Result(data=saved)


@dataclass
class GetVideoQuery:
    video_id: str = ""


class GetVideoQueryHandler:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def handle(self, query: GetVideoQuery) -> Result:
        try:
            video_id = VideoId(query.video_id)
        except ValueError as e:
            return Result(success=False, error=str(e), error_code="INVALID_VIDEO_ID")

        video = await self._uow.videos.get_by_video_id(video_id)
        if not video:
            return Result(success=False, error="Video not found", error_code="NOT_FOUND")
        return Result(data=video)


@dataclass
class ListVideosQuery:
    limit: int = 50
    offset: int = 0


class ListVideosQueryHandler:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def handle(self, query: ListVideosQuery) -> Result:
        videos = await self._uow.videos.list_all(limit=query.limit, offset=query.offset)
        return Result(data=videos)
