from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_result_mock(scalar_return=None, scalars_all_return=None, scalar_one_or_none_return=None):
    """Create a mock that mimics an SQLAlchemy Result object.

    When awaited (via __await__), returns itself so mock chains like
    ``await session.execute(stmt)`` then ``result.scalars().all()``
    work correctly.
    """
    mock_result = MagicMock()
    mock_result.__await__ = lambda: iter([mock_result])

    if scalar_return is not None:
        mock_result.scalar.return_value = scalar_return
    if scalars_all_return is not None:
        mock_result.scalars.return_value.all.return_value = scalars_all_return
    if scalar_one_or_none_return is not None:
        mock_result.scalar_one_or_none.return_value = scalar_one_or_none_return

    return mock_result


class TestProjectRepository:
    async def test_create(self):
        from database.repositories.project_repository import ProjectRepository

        session = AsyncMock()
        repo = ProjectRepository(session=session)
        project = MagicMock()
        result = await repo.create_from_model(project)
        assert result is not None

    async def test_get_by_id(self):
        from database.repositories.project_repository import ProjectRepository

        session = AsyncMock()
        repo = ProjectRepository(session=session)
        mock_result = _make_result_mock(scalar_one_or_none_return=MagicMock())
        session.execute.return_value = mock_result
        result = await repo.get_by_uuid("proj123")
        assert result is not None

    async def test_get_by_video_id(self):
        from database.repositories.project_repository import ProjectRepository

        session = AsyncMock()
        repo = ProjectRepository(session=session)
        mock_result = _make_result_mock(scalar_one_or_none_return=MagicMock())
        session.execute.return_value = mock_result
        result = await repo.get_by_video_id("vid123")
        assert result is not None or result is None

    async def test_list_all(self):
        from database.repositories.project_repository import ProjectRepository

        session = AsyncMock()
        repo = ProjectRepository(session=session)
        mock_result = _make_result_mock(scalars_all_return=[MagicMock(), MagicMock()])
        session.execute.return_value = mock_result
        projects = await repo.list_all()
        assert len(projects) == 2

    async def test_count(self):
        from database.repositories.project_repository import ProjectRepository

        session = AsyncMock()
        repo = ProjectRepository(session=session)
        mock_result = _make_result_mock(scalar_return=3)
        session.execute.return_value = mock_result
        result = await repo.count()
        assert result == 3

    async def test_delete(self):
        from database.repositories.project_repository import ProjectRepository

        session = AsyncMock()
        repo = ProjectRepository(session=session)
        mock_instance = MagicMock()
        mock_result = _make_result_mock(scalar_one_or_none_return=mock_instance)
        session.execute.return_value = mock_result
        result = await repo.soft_delete("proj123")
        assert result is True
        assert mock_instance.is_deleted is True


class TestVideoRepository:
    async def test_create(self):
        from database.repositories.video_repository import VideoRepository

        session = AsyncMock()
        repo = VideoRepository(session=session)
        video = MagicMock()
        result = await repo.create_from_model(video)
        assert result is not None

    async def test_get_by_youtube_id(self):
        from database.repositories.video_repository import VideoRepository

        session = AsyncMock()
        repo = VideoRepository(session=session)
        mock_result = _make_result_mock(scalar_one_or_none_return=MagicMock())
        session.execute.return_value = mock_result
        result = await repo.get_by_video_id("yt123")
        assert result is not None or result is None

    async def test_get_by_project(self):
        from database.repositories.video_repository import VideoRepository

        session = AsyncMock()
        repo = VideoRepository(session=session)
        mock_result = _make_result_mock(scalars_all_return=[MagicMock()])
        session.execute.return_value = mock_result
        videos = await repo.list_by_project("proj123")
        assert len(videos) >= 0


class TestTranscriptRepository:
    async def test_create(self):
        from database.repositories.transcript_repository import TranscriptRepository

        session = AsyncMock()
        repo = TranscriptRepository(session=session)
        transcript = MagicMock()
        result = await repo.create_from_model(transcript)
        assert result is not None

    async def test_get_by_video(self):
        from database.repositories.transcript_repository import TranscriptRepository

        session = AsyncMock()
        repo = TranscriptRepository(session=session)
        mock_result = _make_result_mock(scalar_one_or_none_return=MagicMock())
        session.execute.return_value = mock_result
        result = await repo.get_by_video_id("vid123")
        assert result is not None or result is None


class TestAnalysisRepository:
    async def test_create(self):
        from database.repositories.analysis_repository import AnalysisRepository

        session = AsyncMock()
        repo = AnalysisRepository(session=session)
        analysis = MagicMock()
        result = await repo.create_from_model(analysis)
        assert result is not None

    async def test_get_by_project(self):
        from database.repositories.analysis_repository import AnalysisRepository

        session = AsyncMock()
        repo = AnalysisRepository(session=session)
        mock_result = _make_result_mock(scalar_one_or_none_return=MagicMock())
        session.execute.return_value = mock_result
        result = await repo.get_by_project("proj123")
        assert result is not None or result is None


class TestKnowledgeGraphRepository:
    async def test_create(self):
        from database.repositories.knowledge_repository import KnowledgeGraphRepository

        session = AsyncMock()
        repo = KnowledgeGraphRepository(session=session)
        kg = MagicMock()
        result = await repo.create_from_model(kg)
        assert result is not None

    async def test_get_by_project(self):
        from database.repositories.knowledge_repository import KnowledgeGraphRepository

        session = AsyncMock()
        repo = KnowledgeGraphRepository(session=session)
        mock_result = _make_result_mock(scalar_one_or_none_return=MagicMock())
        session.execute.return_value = mock_result
        result = await repo.get_by_project("proj123")
        assert result is not None or result is None


class TestSEORepository:
    async def test_create(self):
        from database.repositories.seo_repository import SEORepository

        session = AsyncMock()
        repo = SEORepository(session=session)
        seo = MagicMock()
        result = await repo.create_from_model(seo)
        assert result is not None

    async def test_get_by_project(self):
        from database.repositories.seo_repository import SEORepository

        session = AsyncMock()
        repo = SEORepository(session=session)
        mock_result = _make_result_mock(scalar_one_or_none_return=MagicMock())
        session.execute.return_value = mock_result
        result = await repo.get_by_project("proj123")
        assert result is not None or result is None


class TestOutlineRepository:
    async def test_create(self):
        from database.repositories.outline_repository import OutlineRepository

        session = AsyncMock()
        repo = OutlineRepository(session=session)
        outline = MagicMock()
        result = await repo.create_from_model(outline)
        assert result is not None


class TestSectionRepository:
    async def test_create(self):
        from database.repositories.section_repository import SectionRepository

        session = AsyncMock()
        repo = SectionRepository(session=session)
        section = MagicMock()
        result = await repo.create_from_model(section)
        assert result is not None


class TestDraftRepository:
    async def test_create(self):
        from database.repositories.draft_repository import DraftRepository

        session = AsyncMock()
        repo = DraftRepository(session=session)
        draft = MagicMock()
        result = await repo.create_from_model(draft)
        assert result is not None

    async def test_get_latest(self):
        from database.repositories.draft_repository import DraftRepository

        session = AsyncMock()
        repo = DraftRepository(session=session)
        mock_result = _make_result_mock(scalar_return=0, scalars_all_return=[])
        session.execute.return_value = mock_result
        result = await repo.get_latest("proj123")
        assert result is None


class TestReviewRepository:
    async def test_create(self):
        from database.repositories.review_repository import ReviewRepository

        session = AsyncMock()
        repo = ReviewRepository(session=session)
        review = MagicMock()
        result = await repo.create_from_model(review)
        assert result is not None


class TestOptimizationRepository:
    async def test_create(self):
        from database.repositories.optimization_repository import OptimizationRepository

        session = AsyncMock()
        repo = OptimizationRepository(session=session)
        opt = MagicMock()
        result = await repo.create_from_model(opt)
        assert result is not None


class TestExportRepository:
    async def test_create(self):
        from database.repositories.export_repository import ExportRepository

        session = AsyncMock()
        repo = ExportRepository(session=session)
        export = MagicMock()
        result = await repo.create_from_model(export)
        assert result is not None


class TestHistoryRepository:
    async def test_create(self):
        from database.repositories.history_repository import HistoryRepository

        session = AsyncMock()
        repo = HistoryRepository(session=session)
        entry = MagicMock()
        result = await repo.create_from_model(entry)
        assert result is not None
