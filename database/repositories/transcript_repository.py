from __future__ import annotations

from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.transcript import TranscriptModel
from database.repositories.base import BaseRepository


class TranscriptRepository(BaseRepository[TranscriptModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, TranscriptModel)

    async def get_by_project(self, project_uuid: str) -> TranscriptModel | None:
        return await self.get_by_field("project_uuid", project_uuid)

    async def get_by_video_id(self, video_id: str) -> TranscriptModel | None:
        return await self.get_by_field("video_id", video_id)

    async def get_latest_by_project(
        self, project_uuid: str
    ) -> TranscriptModel | None:
        filters = [TranscriptModel.project_uuid == project_uuid]
        result = await self.paginate(
            page=1, page_size=1,
            order_by="version", descending=True,
            filters=filters,
        )
        return result.items[0] if result.items else None

    async def search_transcripts(
        self, query: str, limit: int = 20
    ) -> Sequence[TranscriptModel]:
        from sqlalchemy import or_
        results = await self.list_all(limit=limit)
        matches = [
            r for r in results
            if query.lower() in (r.plain_text or "").lower()
        ]
        return matches[:limit]


__all__ = ["TranscriptRepository"]
