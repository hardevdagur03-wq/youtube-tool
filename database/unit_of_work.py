from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Self

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import *
from database.repositories.analysis_repository import AnalysisRepository
from database.repositories.draft_repository import DraftRepository
from database.repositories.export_repository import ExportRepository
from database.repositories.history_repository import HistoryRepository, VersionHistoryRepository
from database.repositories.knowledge_repository import KnowledgeGraphRepository
from database.repositories.optimization_repository import OptimizationRepository
from database.repositories.outline_repository import OutlineRepository
from database.repositories.project_repository import ProjectRepository
from database.repositories.review_repository import ReviewRepository
from database.repositories.section_repository import SectionRepository
from database.repositories.seo_repository import SEORepository
from database.repositories.transcript_repository import TranscriptRepository
from database.repositories.video_repository import VideoRepository
from database.session import db_manager

logger = logging.getLogger(__name__)


class UnitOfWork:
    def __init__(self, session: AsyncSession | None = None):
        self._session = session
        self._repositories: dict[str, object] = {}
        self._is_owned_session = session is None

    async def __aenter__(self) -> Self:
        if self._session is None:
            self._session = db_manager.session_factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
        if self._is_owned_session and self._session is not None:
            await self._session.close()

    async def commit(self) -> None:
        if self._session is not None:
            try:
                await self._session.commit()
                logger.debug("Transaction committed")
            except Exception as e:
                logger.error("Commit failed: %s", e)
                await self._session.rollback()
                raise

    async def rollback(self) -> None:
        if self._session is not None:
            await self._session.rollback()
            logger.debug("Transaction rolled back")

    async def flush(self) -> None:
        if self._session is not None:
            await self._session.flush()

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("UnitOfWork not started. Use `async with UnitOfWork():`")
        return self._session

    @property
    def projects(self) -> ProjectRepository:
        return self._repo("projects", ProjectRepository)

    @property
    def videos(self) -> VideoRepository:
        return self._repo("videos", VideoRepository)

    @property
    def transcripts(self) -> TranscriptRepository:
        return self._repo("transcripts", TranscriptRepository)

    @property
    def analyses(self) -> AnalysisRepository:
        return self._repo("analyses", AnalysisRepository)

    @property
    def knowledge_graphs(self) -> KnowledgeGraphRepository:
        return self._repo("knowledge_graphs", KnowledgeGraphRepository)

    @property
    def seo(self) -> SEORepository:
        return self._repo("seo", SEORepository)

    @property
    def outlines(self) -> OutlineRepository:
        return self._repo("outlines", OutlineRepository)

    @property
    def sections(self) -> SectionRepository:
        return self._repo("sections", SectionRepository)

    @property
    def drafts(self) -> DraftRepository:
        return self._repo("drafts", DraftRepository)

    @property
    def reviews(self) -> ReviewRepository:
        return self._repo("reviews", ReviewRepository)

    @property
    def optimizations(self) -> OptimizationRepository:
        return self._repo("optimizations", OptimizationRepository)

    @property
    def exports(self) -> ExportRepository:
        return self._repo("exports", ExportRepository)

    @property
    def history(self) -> HistoryRepository:
        return self._repo("history", HistoryRepository)

    @property
    def version_manager(self) -> "VersionManager":
        from database.version_manager import VersionManager
        key = "version_manager"
        if key not in self._repositories:
            self._repositories[key] = VersionManager(self)
        return self._repositories[key]  # type: ignore[return-value]

    @property
    def version_history(self) -> VersionHistoryRepository:
        return self._repo("version_history", VersionHistoryRepository)

    def _repo(self, name: str, repo_class: type) -> object:
        if name not in self._repositories:
            self._repositories[name] = repo_class(self.session)
        return self._repositories[name]


class TransactionManager:
    @staticmethod
    @asynccontextmanager
    async def transaction() -> AsyncIterator[UnitOfWork]:
        async with UnitOfWork() as uow:
            try:
                yield uow
            except Exception:
                await uow.rollback()
                raise

    @staticmethod
    @asynccontextmanager
    async def read_only() -> AsyncIterator[UnitOfWork]:
        uow = UnitOfWork()
        await uow.__aenter__()
        try:
            yield uow
        finally:
            await uow.__aexit__(None, None, None)
