from __future__ import annotations

from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.draft import DraftModel
from database.repositories.base import BaseRepository


class DraftRepository(BaseRepository[DraftModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, DraftModel)

    async def get_by_project(self, project_uuid: str) -> DraftModel | None:
        return await self.get_by_field("project_uuid", project_uuid)

    async def get_latest_by_project(
        self, project_uuid: str
    ) -> DraftModel | None:
        filters = [DraftModel.project_uuid == project_uuid]
        result = await self.paginate(
            page=1, page_size=1,
            order_by="draft_number", descending=True,
            filters=filters,
        )
        return result.items[0] if result.items else None

    async def list_versions(
        self, project_uuid: str, limit: int = 50
    ) -> Sequence[DraftModel]:
        filters = [DraftModel.project_uuid == project_uuid]
        result = await self.paginate(
            page=1, page_size=limit,
            order_by="draft_number", descending=True,
            filters=filters,
        )
        return result.items

    async def get_latest(self, project_uuid: str) -> DraftModel | None:
        return await self.get_latest_by_project(project_uuid)


__all__ = ["DraftRepository"]
