from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.project import ProjectModel
from database.repositories.base import BaseRepository, PaginatedResult


class ProjectRepository(BaseRepository[ProjectModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ProjectModel)

    async def get_by_project_id(self, project_id: str) -> ProjectModel | None:
        return await self.get_by_field("uuid", project_id)

    async def get_by_video_id(self, video_id: str) -> ProjectModel | None:
        return await self.get_by_field("video_id", video_id)

    async def get_by_short_id(self, short_id: str) -> ProjectModel | None:
        return await self.get_by_field("short_id", short_id)

    async def list_by_status(
        self, status: str, page: int = 1, page_size: int = 20
    ) -> PaginatedResult[ProjectModel]:
        from sqlalchemy import ColumnExpressionArgument as CEA
        return await self.paginate(
            page=page,
            page_size=page_size,
            order_by="updated_at",
            descending=True,
            filters=[ProjectModel.status == status],
        )

    async def list_recent(
        self, limit: int = 10
    ) -> Sequence[ProjectModel]:
        return await self.list_all(order_by="updated_at", descending=True, limit=limit)

    async def update_pipeline_state(
        self, uuid: str, state: dict[str, Any]
    ) -> ProjectModel | None:
        return await self.update(uuid, pipeline_state=state)

    async def update_stage_data(
        self, uuid: str, stage: str, data: dict[str, Any]
    ) -> ProjectModel | None:
        project = await self.get_by_uuid(uuid)
        if project is None:
            return None
        stage_data = dict(project.stage_data or {})
        stage_data[stage] = data
        return await self.update(uuid, stage_data=stage_data)

    async def update_status(
        self, uuid: str, status: str
    ) -> ProjectModel | None:
        return await self.update(uuid, status=status)

    async def search_projects(
        self, query: str, page: int = 1, page_size: int = 20
    ) -> PaginatedResult[ProjectModel]:
        return await self.paginate(
            page=page,
            page_size=page_size,
            order_by="updated_at",
            descending=True,
            search_text=query,
            search_columns=["name", "description", "video_id", "tags"],
        )

    async def get_project_stats(self) -> dict[str, Any]:
        total = await self.count()
        from sqlalchemy import func
        stmt = (
            select(ProjectModel.status, func.count(ProjectModel.uuid))
            .where(ProjectModel.is_deleted == False)
            .group_by(ProjectModel.status)
        )
        result = await self.session.execute(stmt)
        by_status = {row[0]: row[1] for row in result}

        return {
            "total_projects": total,
            "by_status": by_status,
        }
