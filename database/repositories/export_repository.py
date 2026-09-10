from __future__ import annotations

from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.export import ExportModel
from database.repositories.base import BaseRepository


class ExportRepository(BaseRepository[ExportModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ExportModel)

    async def list_by_project(
        self, project_uuid: str
    ) -> Sequence[ExportModel]:
        filters = [ExportModel.project_uuid == project_uuid]
        result = await self.paginate(
            page=1, page_size=50,
            order_by="created_at", descending=True,
            filters=filters,
        )
        return result.items

    async def get_by_format(
        self, project_uuid: str, export_format: str
    ) -> ExportModel | None:
        from sqlalchemy import and_
        filters = [
            ExportModel.project_uuid == project_uuid,
            ExportModel.export_format == export_format,
        ]
        result = await self.paginate(
            page=1, page_size=1,
            order_by="export_version", descending=True,
            filters=filters,
        )
        return result.items[0] if result.items else None

    async def increment_download_count(self, uuid: str) -> ExportModel | None:
        export = await self.get_by_uuid(uuid)
        if export is None:
            return None
        return await self.update(uuid, download_count=(export.download_count or 0) + 1)

    async def list_by_checksum(
        self, checksum: str
    ) -> Sequence[ExportModel]:
        filters = [ExportModel.checksum == checksum]
        result = await self.paginate(page=1, page_size=10, filters=filters)
        return result.items


__all__ = ["ExportRepository"]
