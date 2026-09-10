from __future__ import annotations

from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.knowledge_graph import KnowledgeGraphModel
from database.repositories.base import BaseRepository


class KnowledgeGraphRepository(BaseRepository[KnowledgeGraphModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, KnowledgeGraphModel)

    async def get_by_project(self, project_uuid: str) -> KnowledgeGraphModel | None:
        return await self.get_by_field("project_uuid", project_uuid)

    async def search_entities(
        self, query: str, limit: int = 20
    ) -> Sequence[KnowledgeGraphModel]:
        results = await self.list_all(limit=limit)
        matches = []
        for kg in results:
            for entity in (kg.entities or []):
                if query.lower() in (entity.get("name", "") or "").lower():
                    matches.append(kg)
                    break
        return matches[:limit]


__all__ = ["KnowledgeGraphRepository"]
