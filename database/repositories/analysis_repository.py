from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.analysis import AnalysisModel
from database.repositories.base import BaseRepository


class AnalysisRepository(BaseRepository[AnalysisModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, AnalysisModel)

    async def get_by_project(self, project_uuid: str) -> AnalysisModel | None:
        return await self.get_by_field("project_uuid", project_uuid)


__all__ = ["AnalysisRepository"]
