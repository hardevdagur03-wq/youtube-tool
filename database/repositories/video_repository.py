from __future__ import annotations

from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.video import VideoModel
from database.repositories.base import BaseRepository


class VideoRepository(BaseRepository[VideoModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, VideoModel)

    async def get_by_video_id(self, video_id: str) -> VideoModel | None:
        return await self.get_by_field("video_id", video_id)

    async def list_by_project(self, project_uuid: str) -> Sequence[VideoModel]:
        return await self.list_all(
            order_by="created_at", descending=True, limit=50, offset=0
        )

    async def get_recent_by_channel(
        self, channel_id: str, limit: int = 10
    ) -> Sequence[VideoModel]:
        filters = [VideoModel.channel_id == channel_id]
        result = await self.paginate(
            page=1, page_size=limit,
            order_by="published_at", descending=True,
            filters=filters,
        )
        return result.items


__all__ = ["VideoRepository"]
