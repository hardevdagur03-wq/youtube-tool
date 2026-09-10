from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.optimization import OptimizationModel
from database.repositories.base import BaseRepository


class OptimizationRepository(BaseRepository[OptimizationModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, OptimizationModel)

    async def get_by_project(self, project_uuid: str) -> OptimizationModel | None:
        return await self.get_by_field("project_uuid", project_uuid)

    async def get_by_draft(self, draft_uuid: str) -> OptimizationModel | None:
        return await self.get_by_field("draft_uuid", draft_uuid)

    async def get_latest_by_project(
        self, project_uuid: str
    ) -> OptimizationModel | None:
        filters = [OptimizationModel.project_uuid == project_uuid]
        result = await self.paginate(
            page=1, page_size=1,
            order_by="optimization_round", descending=True,
            filters=filters,
        )
        return result.items[0] if result.items else None


__all__ = ["OptimizationRepository"]
