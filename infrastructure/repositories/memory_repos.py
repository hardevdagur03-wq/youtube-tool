"""In-memory repository implementations for testing and development.

These implement the repository interfaces defined in domain/repositories.py.
"""

from __future__ import annotations

import copy
from typing import Any

from domain.entities import (
    Analysis,
    Blog,
    Export,
    KnowledgeGraph,
    Outline,
    Project,
    SEO,
    Transcript,
    Video,
)
from domain.repositories import (
    AnalysisRepository,
    BlogRepository,
    ExportRepository,
    KnowledgeGraphRepository,
    OutlineRepository,
    ProjectRepository,
    SEORepository,
    TranscriptRepository,
    UnitOfWork,
    VideoRepository,
)
from domain.value_objects import PipelineStatus, VideoId


class InMemoryVideoRepository(VideoRepository):
    def __init__(self) -> None:
        self._store: dict[str, Video] = {}

    async def save(self, video: Video) -> Video:
        self._store[video.id] = copy.deepcopy(video)
        return video

    async def get_by_id(self, video_id: str) -> Video | None:
        return copy.deepcopy(self._store.get(video_id))

    async def get_by_video_id(self, video_id: VideoId) -> Video | None:
        for v in self._store.values():
            if v.video_id == video_id:
                return copy.deepcopy(v)
        return None

    async def delete(self, video_id: str) -> bool:
        return bool(self._store.pop(video_id, None))

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Video]:
        items = list(self._store.values())[offset:offset + limit]
        return copy.deepcopy(items)

    async def search(self, query: str, limit: int = 20) -> list[Video]:
        results = []
        query_lower = query.lower()
        for v in self._store.values():
            if query_lower in v.title.lower() or query_lower in v.video_id.value:
                results.append(v)
                if len(results) >= limit:
                    break
        return copy.deepcopy(results)

    def clear(self) -> None:
        self._store.clear()


class InMemoryTranscriptRepository(TranscriptRepository):
    def __init__(self) -> None:
        self._store: dict[str, Transcript] = {}

    async def save(self, transcript: Transcript) -> Transcript:
        self._store[transcript.id] = copy.deepcopy(transcript)
        return transcript

    async def get_by_id(self, transcript_id: str) -> Transcript | None:
        return copy.deepcopy(self._store.get(transcript_id))

    async def get_by_video_id(self, video_id: VideoId) -> Transcript | None:
        for t in self._store.values():
            if t.video_id == video_id:
                return copy.deepcopy(t)
        return None

    async def delete(self, transcript_id: str) -> bool:
        return bool(self._store.pop(transcript_id, None))

    def clear(self) -> None:
        self._store.clear()


class InMemoryAnalysisRepository(AnalysisRepository):
    def __init__(self) -> None:
        self._store: dict[str, Analysis] = {}

    async def save(self, analysis: Analysis) -> Analysis:
        self._store[analysis.id] = copy.deepcopy(analysis)
        return analysis

    async def get_by_id(self, analysis_id: str) -> Analysis | None:
        return copy.deepcopy(self._store.get(analysis_id))

    async def get_by_video_id(self, video_id: VideoId) -> Analysis | None:
        for a in self._store.values():
            if a.video_id == video_id:
                return copy.deepcopy(a)
        return None

    async def delete(self, analysis_id: str) -> bool:
        return bool(self._store.pop(analysis_id, None))

    def clear(self) -> None:
        self._store.clear()


class InMemoryBlogRepository(BlogRepository):
    def __init__(self) -> None:
        self._store: dict[str, Blog] = {}

    async def save(self, blog: Blog) -> Blog:
        self._store[blog.id] = copy.deepcopy(blog)
        return blog

    async def get_by_id(self, blog_id: str) -> Blog | None:
        return copy.deepcopy(self._store.get(blog_id))

    async def get_by_video_id(self, video_id: VideoId) -> Blog | None:
        for b in self._store.values():
            if b.video_id == video_id:
                return copy.deepcopy(b)
        return None

    async def delete(self, blog_id: str) -> bool:
        return bool(self._store.pop(blog_id, None))

    def clear(self) -> None:
        self._store.clear()


class InMemorySEORepository(SEORepository):
    def __init__(self) -> None:
        self._store: dict[str, SEO] = {}

    async def save(self, seo: SEO) -> SEO:
        self._store[seo.id] = copy.deepcopy(seo)
        return seo

    async def get_by_id(self, seo_id: str) -> SEO | None:
        return copy.deepcopy(self._store.get(seo_id))

    async def get_by_video_id(self, video_id: VideoId) -> SEO | None:
        for s in self._store.values():
            if s.video_id == video_id:
                return copy.deepcopy(s)
        return None

    async def delete(self, seo_id: str) -> bool:
        return bool(self._store.pop(seo_id, None))

    def clear(self) -> None:
        self._store.clear()


class InMemoryExportRepository(ExportRepository):
    def __init__(self) -> None:
        self._store: dict[str, Export] = {}

    async def save(self, export: Export) -> Export:
        self._store[export.id] = copy.deepcopy(export)
        return export

    async def get_by_id(self, export_id: str) -> Export | None:
        return copy.deepcopy(self._store.get(export_id))

    async def get_by_video_id(self, video_id: VideoId) -> Export | None:
        for e in self._store.values():
            if e.video_id == video_id:
                return copy.deepcopy(e)
        return None

    async def delete(self, export_id: str) -> bool:
        return bool(self._store.pop(export_id, None))

    def clear(self) -> None:
        self._store.clear()


class InMemoryProjectRepository(ProjectRepository):
    def __init__(self) -> None:
        self._store: dict[str, Project] = {}

    async def save(self, project: Project) -> Project:
        self._store[project.id] = copy.deepcopy(project)
        return project

    async def get_by_id(self, project_id: str) -> Project | None:
        return copy.deepcopy(self._store.get(project_id))

    async def get_by_video_id(self, video_id: VideoId) -> Project | None:
        for p in self._store.values():
            if p.video_id == video_id:
                return copy.deepcopy(p)
        return None

    async def delete(self, project_id: str) -> bool:
        return bool(self._store.pop(project_id, None))

    async def list_all(
        self, limit: int = 100, offset: int = 0, status: PipelineStatus | None = None
    ) -> list[Project]:
        items = list(self._store.values())
        if status:
            items = [p for p in items if p.status == status]
        items = items[offset:offset + limit]
        return copy.deepcopy(items)

    async def search(self, query: str, limit: int = 20) -> list[Project]:
        results = []
        query_lower = query.lower()
        for p in self._store.values():
            if query_lower in p.title.lower():
                results.append(p)
                if len(results) >= limit:
                    break
        return copy.deepcopy(results)

    async def update_status(
        self, project_id: str, status: PipelineStatus
    ) -> Project | None:
        project = self._store.get(project_id)
        if project:
            project.status = status
            return copy.deepcopy(project)
        return None

    def clear(self) -> None:
        self._store.clear()


class InMemoryKnowledgeGraphRepository(KnowledgeGraphRepository):
    def __init__(self) -> None:
        self._store: dict[str, KnowledgeGraph] = {}

    async def save(self, kg: KnowledgeGraph) -> KnowledgeGraph:
        self._store[kg.id] = copy.deepcopy(kg)
        return kg

    async def get_by_video_id(self, video_id: VideoId) -> KnowledgeGraph | None:
        for kg in self._store.values():
            if kg.video_id == video_id:
                return copy.deepcopy(kg)
        return None

    async def delete(self, kg_id: str) -> bool:
        return bool(self._store.pop(kg_id, None))

    def clear(self) -> None:
        self._store.clear()


class InMemoryOutlineRepository(OutlineRepository):
    def __init__(self) -> None:
        self._store: dict[str, Outline] = {}

    async def save(self, outline: Outline) -> Outline:
        self._store[outline.id] = copy.deepcopy(outline)
        return outline

    async def get_by_video_id(self, video_id: VideoId) -> Outline | None:
        for o in self._store.values():
            if o.video_id == video_id:
                return copy.deepcopy(o)
        return None

    async def delete(self, outline_id: str) -> bool:
        return bool(self._store.pop(outline_id, None))

    def clear(self) -> None:
        self._store.clear()


class InMemoryUnitOfWork(UnitOfWork):
    """In-memory Unit of Work for testing.

    All repositories share the same in-memory stores.
    """

    def __init__(self) -> None:
        self._videos = InMemoryVideoRepository()
        self._transcripts = InMemoryTranscriptRepository()
        self._analyses = InMemoryAnalysisRepository()
        self._blogs = InMemoryBlogRepository()
        self._seos = InMemorySEORepository()
        self._exports = InMemoryExportRepository()
        self._projects = InMemoryProjectRepository()
        self._kgs = InMemoryKnowledgeGraphRepository()
        self._outlines = InMemoryOutlineRepository()
        self._committed = False

    @property
    def videos(self) -> VideoRepository:
        return self._videos

    @property
    def transcripts(self) -> TranscriptRepository:
        return self._transcripts

    @property
    def analyses(self) -> AnalysisRepository:
        return self._analyses

    @property
    def blogs(self) -> BlogRepository:
        return self._blogs

    @property
    def seos(self) -> SEORepository:
        return self._seos

    @property
    def exports(self) -> ExportRepository:
        return self._exports

    @property
    def projects(self) -> ProjectRepository:
        return self._projects

    @property
    def knowledge_graphs(self) -> KnowledgeGraphRepository:
        return self._kgs

    @property
    def outlines(self) -> OutlineRepository:
        return self._outlines

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        pass

    async def __aenter__(self) -> InMemoryUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: object = None,
    ) -> None:
        if exc_type and not self._committed:
            await self.rollback()

    def clear_all(self) -> None:
        self._videos.clear()
        self._transcripts.clear()
        self._analyses.clear()
        self._blogs.clear()
        self._seos.clear()
        self._exports.clear()
        self._projects.clear()
        self._kgs.clear()
        self._outlines.clear()
