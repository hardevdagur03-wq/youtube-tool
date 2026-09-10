"""Repository interfaces for the domain layer.

These are abstract interfaces that the infrastructure layer implements.
The domain layer depends on these abstractions, not on implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, Protocol, TypeVar

from domain.common.base import AggregateRoot, Repository
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
from domain.value_objects import PipelineStage, PipelineStatus, VideoId

T = TypeVar("T", bound=AggregateRoot)


class RepositoryProtocol(Protocol[T]):
    async def save(self, entity: T) -> T: ...
    async def get_by_id(self, entity_id: str) -> T | None: ...
    async def delete(self, entity_id: str) -> bool: ...
    async def list_all(self, limit: int = 100, offset: int = 0) -> list[T]: ...


class VideoRepository(Repository, ABC):
    @abstractmethod
    async def save(self, video: Video) -> Video:
        ...

    @abstractmethod
    async def get_by_id(self, video_id: str) -> Video | None:
        ...

    @abstractmethod
    async def get_by_video_id(self, video_id: VideoId) -> Video | None:
        ...

    @abstractmethod
    async def delete(self, video_id: str) -> bool:
        ...

    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Video]:
        ...

    @abstractmethod
    async def search(self, query: str, limit: int = 20) -> list[Video]:
        ...


class TranscriptRepository(Repository, ABC):
    @abstractmethod
    async def save(self, transcript: Transcript) -> Transcript:
        ...

    @abstractmethod
    async def get_by_id(self, transcript_id: str) -> Transcript | None:
        ...

    @abstractmethod
    async def get_by_video_id(self, video_id: VideoId) -> Transcript | None:
        ...

    @abstractmethod
    async def delete(self, transcript_id: str) -> bool:
        ...


class AnalysisRepository(Repository, ABC):
    @abstractmethod
    async def save(self, analysis: Analysis) -> Analysis:
        ...

    @abstractmethod
    async def get_by_id(self, analysis_id: str) -> Analysis | None:
        ...

    @abstractmethod
    async def get_by_video_id(self, video_id: VideoId) -> Analysis | None:
        ...

    @abstractmethod
    async def delete(self, analysis_id: str) -> bool:
        ...


class BlogRepository(Repository, ABC):
    @abstractmethod
    async def save(self, blog: Blog) -> Blog:
        ...

    @abstractmethod
    async def get_by_id(self, blog_id: str) -> Blog | None:
        ...

    @abstractmethod
    async def get_by_video_id(self, video_id: VideoId) -> Blog | None:
        ...

    @abstractmethod
    async def delete(self, blog_id: str) -> bool:
        ...


class SEORepository(Repository, ABC):
    @abstractmethod
    async def save(self, seo: SEO) -> SEO:
        ...

    @abstractmethod
    async def get_by_id(self, seo_id: str) -> SEO | None:
        ...

    @abstractmethod
    async def get_by_video_id(self, video_id: VideoId) -> SEO | None:
        ...

    @abstractmethod
    async def delete(self, seo_id: str) -> bool:
        ...


class ExportRepository(Repository, ABC):
    @abstractmethod
    async def save(self, export: Export) -> Export:
        ...

    @abstractmethod
    async def get_by_id(self, export_id: str) -> Export | None:
        ...

    @abstractmethod
    async def get_by_video_id(self, video_id: VideoId) -> Export | None:
        ...

    @abstractmethod
    async def delete(self, export_id: str) -> bool:
        ...


class ProjectRepository(Repository, ABC):
    @abstractmethod
    async def save(self, project: Project) -> Project:
        ...

    @abstractmethod
    async def get_by_id(self, project_id: str) -> Project | None:
        ...

    @abstractmethod
    async def get_by_video_id(self, video_id: VideoId) -> Project | None:
        ...

    @abstractmethod
    async def delete(self, project_id: str) -> bool:
        ...

    @abstractmethod
    async def list_all(
        self, limit: int = 100, offset: int = 0, status: PipelineStatus | None = None
    ) -> list[Project]:
        ...

    @abstractmethod
    async def search(self, query: str, limit: int = 20) -> list[Project]:
        ...

    @abstractmethod
    async def update_status(
        self, project_id: str, status: PipelineStatus
    ) -> Project | None:
        ...


class KnowledgeGraphRepository(Repository, ABC):
    @abstractmethod
    async def save(self, kg: KnowledgeGraph) -> KnowledgeGraph:
        ...

    @abstractmethod
    async def get_by_video_id(self, video_id: VideoId) -> KnowledgeGraph | None:
        ...

    @abstractmethod
    async def delete(self, kg_id: str) -> bool:
        ...


class OutlineRepository(Repository, ABC):
    @abstractmethod
    async def save(self, outline: Outline) -> Outline:
        ...

    @abstractmethod
    async def get_by_video_id(self, video_id: VideoId) -> Outline | None:
        ...

    @abstractmethod
    async def delete(self, outline_id: str) -> bool:
        ...


class UnitOfWork(ABC):
    """Unit of Work interface for coordinating repository operations.

    Implementation is in the infrastructure layer.
    """

    videos: VideoRepository
    transcripts: TranscriptRepository
    analyses: AnalysisRepository
    blogs: BlogRepository
    seos: SEORepository
    exports: ExportRepository
    projects: ProjectRepository
    knowledge_graphs: KnowledgeGraphRepository
    outlines: OutlineRepository

    @abstractmethod
    async def commit(self) -> None:
        ...

    @abstractmethod
    async def rollback(self) -> None:
        ...

    @abstractmethod
    async def __aenter__(self) -> UnitOfWork:
        ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        ...
