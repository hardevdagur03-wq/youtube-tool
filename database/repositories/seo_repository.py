from __future__ import annotations

from typing import Sequence

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.seo import SEOModel
from database.repositories.base import BaseRepository


class SEORepository(BaseRepository[SEOModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, SEOModel)

    async def get_by_project(self, project_uuid: str) -> SEOModel | None:
        return await self.get_by_field("project_uuid", project_uuid)

    async def search_by_keyword(
        self, keyword: str, limit: int = 20
    ) -> Sequence[SEOModel]:
        results = await self.list_all(limit=limit)
        kw_lower = keyword.lower()
        matches = [
            r for r in results
            if kw_lower in (r.primary_keyword or "").lower()
        ]
        return matches[:limit]


__all__ = ["SEORepository"]
