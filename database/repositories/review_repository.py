from __future__ import annotations

from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.review import ReviewModel
from database.repositories.base import BaseRepository


class ReviewRepository(BaseRepository[ReviewModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ReviewModel)

    async def get_by_project(self, project_uuid: str) -> ReviewModel | None:
        return await self.get_by_field("project_uuid", project_uuid)

    async def get_by_draft(self, draft_uuid: str) -> ReviewModel | None:
        return await self.get_by_field("draft_uuid", draft_uuid)

    async def get_latest_by_project(
        self, project_uuid: str
    ) -> ReviewModel | None:
        filters = [ReviewModel.project_uuid == project_uuid]
        result = await self.paginate(
            page=1, page_size=1,
            order_by="version", descending=True,
            filters=filters,
        )
        return result.items[0] if result.items else None

    async def list_recent_reviews(
        self, limit: int = 20
    ) -> Sequence[ReviewModel]:
        return await self.list_all(
            order_by="created_at", descending=True, limit=limit
        )


__all__ = ["ReviewRepository"]
