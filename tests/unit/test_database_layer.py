from __future__ import annotations

import uuid as uuid_lib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class TestBaseRepository:
    async def test_create_entity(self):
        from database.models.project import ProjectModel
        from database.repositories.base import BaseRepository
        repo = BaseRepository(session=AsyncMock(spec=AsyncSession), model_class=ProjectModel)
        result = await repo.create(name="test")
        repo.session.add.assert_called_once()
        repo.session.flush.assert_awaited_once()
        assert result is not None

    async def test_get_by_uuid(self):
        from database.models.project import ProjectModel
        from database.repositories.base import BaseRepository
        repo = BaseRepository(session=AsyncMock(spec=AsyncSession), model_class=ProjectModel)
        exc_result = MagicMock()
        exc_result.scalar_one_or_none.return_value = MagicMock()
        repo.session.execute.return_value = exc_result
        result = await repo.get_by_uuid("some-uuid")
        assert result is not None

    async def test_get_by_uuid_not_found(self):
        from database.models.project import ProjectModel
        from database.repositories.base import BaseRepository
        repo = BaseRepository(session=AsyncMock(spec=AsyncSession), model_class=ProjectModel)
        exc_result = MagicMock()
        exc_result.scalar_one_or_none.return_value = None
        repo.session.execute.return_value = exc_result
        result = await repo.get_by_uuid("some-uuid")
        assert result is None

    async def test_list_all(self):
        from database.models.project import ProjectModel
        from database.repositories.base import BaseRepository
        repo = BaseRepository(session=AsyncMock(spec=AsyncSession), model_class=ProjectModel)
        exc_result = MagicMock()
        exc_result.scalars.return_value.all.return_value = [1, 2, 3]
        repo.session.execute.return_value = exc_result
        result = await repo.list_all()
        assert len(result) == 3

    async def test_count(self):
        from database.models.project import ProjectModel
        from database.repositories.base import BaseRepository
        repo = BaseRepository(session=AsyncMock(spec=AsyncSession), model_class=ProjectModel)
        exc_result = MagicMock()
        exc_result.scalar.return_value = 5
        repo.session.execute.return_value = exc_result
        count = await repo.count()
        assert count == 5

    async def test_soft_delete(self):
        from database.models.project import ProjectModel
        from database.repositories.base import BaseRepository
        repo = BaseRepository(session=AsyncMock(spec=AsyncSession), model_class=ProjectModel)
        entity = MagicMock()
        exc_result = MagicMock()
        exc_result.scalar_one_or_none.return_value = entity
        repo.session.execute.return_value = exc_result
        result = await repo.soft_delete(str(uuid_lib.uuid4()))
        assert result is True
        repo.session.flush.assert_awaited_once()

    async def test_pagination(self):
        from database.models.project import ProjectModel
        from database.repositories.base import BaseRepository
        repo = BaseRepository(session=AsyncMock(spec=AsyncSession), model_class=ProjectModel)
        exc_result = MagicMock()
        exc_result.scalars.return_value.all.return_value = [1, 2]
        exc_result.scalar.return_value = 10
        repo.session.execute.return_value = exc_result
        result = await repo.paginate(page=1, page_size=10)
        assert len(result.items) == 2


class TestUnitOfWork:
    async def test_commit(self):
        from database.unit_of_work import UnitOfWork
        session = AsyncMock(spec=AsyncSession)
        uow = UnitOfWork(session=session)
        await uow.__aenter__()
        await uow.commit()
        session.commit.assert_awaited_once()

    async def test_rollback(self):
        from database.unit_of_work import UnitOfWork
        session = AsyncMock(spec=AsyncSession)
        uow = UnitOfWork(session=session)
        await uow.__aenter__()
        await uow.rollback()
        session.rollback.assert_awaited_once()

    async def test_context_manager(self):
        from database.unit_of_work import UnitOfWork
        session = AsyncMock(spec=AsyncSession)
        async with UnitOfWork(session=session) as uow:
            await uow.commit()


class TestTransactionManager:
    async def test_transaction_success(self):
        from database.unit_of_work import TransactionManager
        with patch("database.unit_of_work.db_manager") as mock_mgr:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_mgr.session_factory.return_value = mock_session
            async with TransactionManager.transaction() as uow:
                pass

    async def test_transaction_rollback_on_error(self):
        from database.unit_of_work import TransactionManager
        with patch("database.unit_of_work.db_manager") as mock_mgr:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_mgr.session_factory.return_value = mock_session
            with pytest.raises(ValueError):
                async with TransactionManager.transaction():
                    raise ValueError("test error")


class TestVersionManager:
    async def test_create_version(self):
        from database.version_manager import VersionManager
        uow = MagicMock()
        uow.version_history = MagicMock()
        uow.version_history.get_latest_version = AsyncMock(return_value=None)
        uow.version_history.create = AsyncMock()
        uow.history = MagicMock()
        uow.history.log_event = AsyncMock()
        vm = VersionManager(uow=uow)
        version = await vm.create_version(
            entity_type="project", entity_uuid="123",
            project_uuid="p123", snapshot={"name": "test"},
        )
        assert version == 1

    async def test_list_versions(self):
        from database.version_manager import VersionManager
        uow = MagicMock()
        uow.version_history = MagicMock()
        uow.version_history.list_by_entity = AsyncMock(return_value=[])
        vm = VersionManager(uow=uow)
        history = await vm.list_versions("project", "123")
        assert len(history) == 0


class TestRollbackEngine:
    async def test_rollback(self):
        from database.rollback_engine import RollbackEngine
        uow = MagicMock()
        uow.version_history = MagicMock()
        uow.version_history.get_version = AsyncMock(return_value=None)
        engine = RollbackEngine(uow=uow)
        with pytest.raises(ValueError):
            await engine.rollback(
                entity_type="project", entity_uuid="123", target_version=1,
            )


class TestResumeEngine:
    async def test_get_checkpoint(self):
        from database.resume_engine import ResumeEngine
        uow = MagicMock()
        uow.projects = MagicMock()
        uow.projects.get_by_uuid = AsyncMock(return_value=None)
        engine = ResumeEngine(uow=uow)
        checkpoint = await engine.get_pipeline_checkpoint(project_uuid="test123")
        assert checkpoint is None

    async def test_save_checkpoint(self):
        from database.resume_engine import ResumeEngine
        uow = MagicMock()
        project = MagicMock()
        project.pipeline_state = {}
        uow.projects = MagicMock()
        uow.projects.get_by_uuid = AsyncMock(return_value=project)
        uow.projects.update_pipeline_state = AsyncMock()
        engine = ResumeEngine(uow=uow)
        await engine.save_pipeline_checkpoint(
            project_uuid="test123", stage="metadata", checkpoint_data={},
        )


class TestAuditService:
    async def test_log_event(self):
        from database.audit import AuditService
        uow = MagicMock()
        uow.history = MagicMock()
        uow.history.log_event = AsyncMock()
        svc = AuditService(uow=uow)
        await svc.log(
            action="test_action", entity_type="project",
            entity_uuid="123", project_uuid="p123",
        )

    async def test_get_events(self):
        from database.audit import AuditService
        uow = MagicMock()
        uow.history = MagicMock()
        uow.history.list_by_entity = AsyncMock(return_value=[])
        svc = AuditService(uow=uow)
        events = await svc.get_entity_history(entity_type="project", entity_uuid="123")
        assert len(events) == 0


class TestFullTextSearch:
    async def test_search(self):
        from database.search import FullTextSearch
        session = AsyncMock(spec=AsyncSession)
        search = FullTextSearch(session=session)
        with patch.object(search, "_search_projects", AsyncMock(return_value=([], 0))):
            with patch.object(search, "_search_transcripts", AsyncMock(return_value=([], 0))):
                with patch.object(search, "_search_videos", AsyncMock(return_value=([], 0))):
                    results = await search.search(query="Python")
                    assert isinstance(results.items, list)

    async def test_search_empty(self):
        from database.search import FullTextSearch
        session = AsyncMock(spec=AsyncSession)
        search = FullTextSearch(session=session)
        with patch.object(search, "_search_projects", AsyncMock(return_value=([], 0))):
            with patch.object(search, "_search_transcripts", AsyncMock(return_value=([], 0))):
                with patch.object(search, "_search_videos", AsyncMock(return_value=([], 0))):
                    results = await search.search("")
                    assert results.items == []


class TestDatabaseCache:
    async def test_set_and_get(self):
        from database.cache import DatabaseCache
        cache = DatabaseCache()
        await cache.set("test_ns", "test_key", {"data": "test_value"})
        result = await cache.get("test_ns", "test_key")
        assert result == {"data": "test_value"}

    async def test_cache_miss(self):
        from database.cache import DatabaseCache
        cache = DatabaseCache()
        result = await cache.get("test_ns", "nonexistent")
        assert result is None

    async def test_namespace_invalidation(self):
        from database.cache import DatabaseCache
        cache = DatabaseCache()
        await cache.set("ns", "key1", "value1")
        await cache.set("ns", "key2", "value2")
        await cache.invalidate_namespace("ns")
        assert await cache.get("ns", "key1") is None
        assert await cache.get("ns", "key2") is None


class TestDatabaseService:
    async def test_create_project(self):
        from database.db_service import DatabaseService
        with patch("database.db_service.db_manager") as mock_mgr:
            mock_mgr._engine = MagicMock()
            mock_session = AsyncMock()
            mock_mgr.session_factory = MagicMock(return_value=mock_session)
            svc = DatabaseService()
            result = await svc.create_project(name="Test Project", video_id="test123")
            assert result is not None

    async def test_get_project(self):
        from database.db_service import DatabaseService
        with patch("database.db_service.db_manager") as mock_mgr:
            mock_mgr._engine = MagicMock()
            mock_session = AsyncMock()
            exc_result = MagicMock()
            exc_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = exc_result
            mock_mgr.session_factory = MagicMock(return_value=mock_session)
            svc = DatabaseService()
            result = await svc.get_project("nonexistent")
            assert result is None

    async def test_health_check(self):
        from database.db_service import DatabaseService
        with patch("database.db_service.db_manager") as mock_mgr:
            mock_mgr._engine = MagicMock()
            mock_session = AsyncMock()
            exc_result = MagicMock()
            exc_result.scalar.return_value = 0
            mock_session.execute.return_value = exc_result
            mock_mgr.session_factory = MagicMock(return_value=mock_session)
            svc = DatabaseService()
            health = await svc.health_check()
            assert "healthy" in health

    async def test_list_projects(self):
        from database.db_service import DatabaseService
        with patch("database.db_service.db_manager") as mock_mgr:
            mock_mgr._engine = MagicMock()
            mock_session = AsyncMock()
            exc_result = MagicMock()
            exc_result.scalars.return_value.all.return_value = []
            mock_session.execute.return_value = exc_result
            mock_mgr.session_factory = MagicMock(return_value=mock_session)
            svc = DatabaseService()
            projects = await svc.list_projects()
            assert isinstance(projects, list)


class TestModelRelationships:
    def test_project_video_relationship(self):
        from database.base import Base
        assert Base is not None

    def test_timestamp_mixin(self):
        from database.base import TimestampMixin
        assert hasattr(TimestampMixin, "created_at")
        assert hasattr(TimestampMixin, "updated_at")

    def test_soft_delete_mixin(self):
        from database.base import SoftDeleteMixin
        assert hasattr(SoftDeleteMixin, "is_deleted")

    def test_version_mixin(self):
        from database.base import VersionMixin
        assert hasattr(VersionMixin, "version")
