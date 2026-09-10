from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.section import SectionModel
from database.repositories.base import BaseRepository


class SectionRepository(BaseRepository[SectionModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, SectionModel)

    async def list_by_project(self, project_uuid: str) -> Sequence[SectionModel]:
        filters = [SectionModel.project_uuid == project_uuid]
        result = await self.paginate(
            page=1, page_size=100,
            order_by="order", descending=False,
            filters=filters,
        )
        return result.items

    async def get_by_heading(
        self, project_uuid: str, heading: str
    ) -> SectionModel | None:
        filters = [
            SectionModel.project_uuid == project_uuid,
            SectionModel.heading == heading,
        ]
        result = await self.paginate(
            page=1, page_size=1, filters=filters,
        )
        return result.items[0] if result.items else None

    async def update_content(
        self, uuid: str, content: str, word_count: int | None = None
    ) -> SectionModel | None:
        kwargs: dict = {"content": content}
        if word_count is not None:
            kwargs["word_count"] = word_count
        return await self.update(uuid, **kwargs)

    async def list_by_status(
        self, project_uuid: str, status: str
    ) -> Sequence[SectionModel]:
        filters = [
            SectionModel.project_uuid == project_uuid,
            SectionModel.status == status,
        ]
        result = await self.paginate(
            page=1, page_size=100,
            order_by="order", descending=False,
            filters=filters,
        )
        return result.items


__all__ = ["SectionRepository"]
