from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.outline import OutlineModel
from database.repositories.base import BaseRepository


class OutlineRepository(BaseRepository[OutlineModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, OutlineModel)

    async def get_by_project(self, project_uuid: str) -> OutlineModel | None:
        return await self.get_by_field("project_uuid", project_uuid)

    async def get_latest_by_project(
        self, project_uuid: str
    ) -> OutlineModel | None:
        filters = [OutlineModel.project_uuid == project_uuid]
        result = await self.paginate(
            page=1, page_size=1,
            order_by="version", descending=True,
            filters=filters,
        )
        return result.items[0] if result.items else None


__all__ = ["OutlineRepository"]
