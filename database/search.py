from __future__ import annotations

import logging
from typing import Any, Sequence

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.project import ProjectModel
from database.models.transcript import TranscriptModel
from database.repositories.base import PaginatedResult, BaseRepository

logger = logging.getLogger(__name__)


class FullTextSearch:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search(
        self,
        query: str,
        entity_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult:
        results: list[dict[str, Any]] = []
        total = 0

        if entity_type is None or entity_type == "project":
            projects, p_total = await self._search_projects(query, page, page_size)
            results.extend(projects)
            total += p_total

        if entity_type is None or entity_type == "transcript":
            transcripts, t_total = await self._search_transcripts(query, page, page_size)
            results.extend(transcripts)
            total += t_total

        if entity_type is None or entity_type == "video":
            videos, v_total = await self._search_videos(query, page, page_size)
            results.extend(videos)
            total += v_total

        return PaginatedResult(
            items=results,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def _search_projects(
        self, query: str, page: int, page_size: int
    ) -> tuple[list[dict[str, Any]], int]:
        q = query.lower()
        stmt = (
            select(ProjectModel)
            .where(
                ProjectModel.is_deleted == False,
                or_(
                    func.lower(ProjectModel.name).like(f"%{q}%"),
                    func.lower(ProjectModel.description).like(f"%{q}%"),
                    ProjectModel.video_id.like(f"%{q}%"),
                    ProjectModel.tags.as_string().like(f"%{q}%"),
                ),
            )
            .order_by(ProjectModel.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        items = result.scalars().all()

        count_stmt = (
            select(func.count(ProjectModel.uuid))
            .where(
                ProjectModel.is_deleted == False,
                or_(
                    func.lower(ProjectModel.name).like(f"%{q}%"),
                    func.lower(ProjectModel.description).like(f"%{q}%"),
                    ProjectModel.video_id.like(f"%{q}%"),
                ),
            )
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        return (
            [{"type": "project", "uuid": p.uuid, "title": p.name, "status": p.status, "updated_at": str(p.updated_at)} for p in items],
            total,
        )

    async def _search_transcripts(
        self, query: str, page: int, page_size: int
    ) -> tuple[list[dict[str, Any]], int]:
        q = query.lower()
        stmt = (
            select(TranscriptModel)
            .where(
                TranscriptModel.is_deleted == False,
                func.lower(TranscriptModel.plain_text).like(f"%{q}%"),
            )
            .order_by(TranscriptModel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        items = result.scalars().all()

        count_stmt = (
            select(func.count(TranscriptModel.uuid))
            .where(
                TranscriptModel.is_deleted == False,
                func.lower(TranscriptModel.plain_text).like(f"%{q}%"),
            )
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        return (
            [{"type": "transcript", "uuid": t.uuid, "project_uuid": t.project_uuid, "language": t.language, "word_count": t.word_count} for t in items],
            total,
        )

    async def _search_videos(
        self, query: str, page: int, page_size: int
    ) -> tuple[list[dict[str, Any]], int]:
        from database.models.video import VideoModel
        q = query.lower()
        stmt = (
            select(VideoModel)
            .where(
                VideoModel.is_deleted == False,
                or_(
                    func.lower(VideoModel.title).like(f"%{q}%"),
                    func.lower(VideoModel.channel_title).like(f"%{q}%"),
                    VideoModel.video_id.like(f"%{q}%"),
                ),
            )
            .order_by(VideoModel.published_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        items = result.scalars().all()

        count_stmt = (
            select(func.count(VideoModel.uuid))
            .where(
                VideoModel.is_deleted == False,
                or_(
                    func.lower(VideoModel.title).like(f"%{q}%"),
                    func.lower(VideoModel.channel_title).like(f"%{q}%"),
                ),
            )
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        return (
            [{"type": "video", "uuid": v.uuid, "title": v.title, "channel": v.channel_title, "video_id": v.video_id} for v in items],
            total,
        )

    async def global_search(
        self, query: str, limit: int = 10
    ) -> dict[str, list[dict[str, Any]]]:
        q = query.lower()
        results: dict[str, list[dict[str, Any]]] = {
            "projects": [],
            "transcripts": [],
            "videos": [],
        }

        p_stmt = (
            select(ProjectModel)
            .where(
                ProjectModel.is_deleted == False,
                or_(
                    func.lower(ProjectModel.name).like(f"%{q}%"),
                    func.lower(ProjectModel.description).like(f"%{q}%"),
                ),
            )
            .order_by(ProjectModel.updated_at.desc())
            .limit(limit)
        )
        p_result = await self.session.execute(p_stmt)
        for p in p_result.scalars().all():
            results["projects"].append({"uuid": p.uuid, "name": p.name, "status": p.status})

        t_stmt = (
            select(TranscriptModel)
            .where(
                TranscriptModel.is_deleted == False,
                func.lower(TranscriptModel.plain_text).like(f"%{q}%"),
            )
            .order_by(TranscriptModel.word_count.desc())
            .limit(limit)
        )
        t_result = await self.session.execute(t_stmt)
        for t in t_result.scalars().all():
            results["transcripts"].append({"uuid": t.uuid, "project_uuid": t.project_uuid, "language": t.language})

        from database.models.video import VideoModel
        v_stmt = (
            select(VideoModel)
            .where(
                VideoModel.is_deleted == False,
                or_(
                    func.lower(VideoModel.title).like(f"%{q}%"),
                    func.lower(VideoModel.channel_title).like(f"%{q}%"),
                ),
            )
            .order_by(VideoModel.view_count.desc())
            .limit(limit)
        )
        v_result = await self.session.execute(v_stmt)
        for v in v_result.scalars().all():
            results["videos"].append({"uuid": v.uuid, "title": v.title, "channel": v.channel_title})

        return results
