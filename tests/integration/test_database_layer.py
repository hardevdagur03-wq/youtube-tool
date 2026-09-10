from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from database.cache import DatabaseCache
from database.config import DatabaseConfig
from database.search import FullTextSearch
from database.session import DatabaseSessionManager
from database.unit_of_work import UnitOfWork


class TestDatabaseLayerIntegration:
    @pytest.mark.asyncio
    async def test_transaction_isolation(self, init_test_database):
        async with init_test_database.session_no_commit() as session:
            uow1 = UnitOfWork(session=session)
            await uow1.__aenter__()
            try:
                await uow1.projects.create(
                    name="Isolation Project", short_id="ISO1",
                    status="created",
                )
            finally:
                await uow1.__aexit__(None, None, None)

        async with init_test_database.session_no_commit() as session:
            uow2 = UnitOfWork(session=session)
            await uow2.__aenter__()
            try:
                all_projs = await uow2.projects.list_all()
                assert any(p.short_id == "ISO1" for p in all_projs)
            finally:
                await uow2.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_rollback_engine(self, uow):
        from database.rollback_engine import RollbackEngine
        from database.version_manager import VersionManager

        p = await uow.projects.create(
            name="Rollback Test", short_id="RBT1", status="COMPLETED",
        )
        await uow.projects.update(p.uuid, name="Modified Name", status="FAILED")

        vm = VersionManager(uow)
        await vm.create_version(
            entity_type="project", entity_uuid=p.uuid,
            project_uuid=p.uuid,
            snapshot={"name": "Rollback Test", "status": "COMPLETED"},
            changed_by="test",
        )

        engine = RollbackEngine(uow)
        result = await engine.rollback_project(p.uuid, 1)
        assert result is not None

        restored = await uow.projects.get_by_uuid(p.uuid)
        assert restored is not None

    @pytest.mark.asyncio
    async def test_resume_engine(self, uow):
        from database.resume_engine import ResumeEngine

        p = await uow.projects.create(
            name="Resume Integration", short_id="RESINT",
            status="FAILED",
            pipeline_state={
                "current_stage": "seo",
                "completed_stages": ["metadata", "transcript", "analysis", "knowledge_graph"],
                "failed_stages": [{"stage": "seo", "error": "API timeout"}],
            },
        )

        engine = ResumeEngine(uow)
        state = await engine.get_resume_state(p.uuid)
        assert state["can_resume"] is True
        assert state["current_stage"] == "seo"

        plan = await engine.compute_resume_plan(p.uuid)
        assert plan["can_resume"] is True
        assert plan["resume_from"] == "seo"

        await engine.mark_stage_completed(p.uuid, "seo")
        updated = await uow.projects.get_by_uuid(p.uuid)
        assert "seo" in updated.pipeline_state.get("completed_stages", [])

    @pytest.mark.asyncio
    async def test_version_tracking_across_updates(self, uow):
        from database.version_manager import VersionManager

        vm = VersionManager(uow)
        p = await uow.projects.create(
            name="Version Track", short_id="VT1", status="created",
        )

        v1 = await vm.create_version(
            entity_type="project", entity_uuid=p.uuid,
            project_uuid=p.uuid,
            snapshot={"name": "Version Track", "status": "created"},
            changed_by="test",
        )
        assert v1 == 1

        await uow.projects.update(p.uuid, name="Updated Name", status="running")
        v2 = await vm.create_version(
            entity_type="project", entity_uuid=p.uuid,
            project_uuid=p.uuid,
            snapshot={"name": "Updated Name", "status": "running"},
            changed_by="test",
        )
        assert v2 == 2

        versions = await vm.list_versions("project", p.uuid)
        assert len(versions) == 2

    @pytest.mark.asyncio
    async def test_audit_logging_for_crud(self, uow):
        from database.audit import AuditService

        audit = AuditService(uow)
        await audit.log_project_event(
            project_uuid="proj-audit-int",
            action="project.created",
            actor_id="user-1",
        )
        await audit.log_project_event(
            project_uuid="proj-audit-int",
            action="project.updated",
            actor_id="user-1",
            changes={"name": {"old": "Old", "new": "New"}},
        )
        await audit.log_pipeline_event(
            project_uuid="proj-audit-int",
            action="pipeline.stage_completed",
            stage="transcript",
        )

        history = await audit.get_project_history("proj-audit-int")
        assert len(history) == 3

        activity = await audit.get_recent_activity(limit=5)
        assert len(activity) >= 3

    @pytest.mark.asyncio
    async def test_full_text_search(self, init_test_database):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            config = DatabaseConfig.for_testing(sqlite_path=path)
            mgr = DatabaseSessionManager()
            mgr.initialize(config)
            await mgr.create_all()

            async with UnitOfWork() as u:
                await u.projects.create(
                    name="Machine Learning Guide",
                    short_id="MLG",
                    description="A comprehensive guide to machine learning",
                )
                await u.videos.create(
                    project_uuid="proj-search", video_id="vid-s1",
                    title="ML Tutorial", channel_title="AI Channel",
                )

            async with mgr.session_no_commit() as session:
                search = FullTextSearch(session)
                results = await search.global_search("Machine")
                assert len(results["projects"]) >= 1

            await mgr.close()
        finally:
            if os.path.exists(path):
                os.unlink(path)

    @pytest.mark.asyncio
    async def test_database_cache(self):
        cache = DatabaseCache(use_redis=False)
        await cache.set("test", "key1", {"data": "cached_value"})
        result = await cache.get("test", "key1")
        assert result == {"data": "cached_value"}

        async def factory():
            return {"data": "fresh_value"}

        cached = await cache.get_or_set("test", "factory_key", factory)
        assert cached == {"data": "fresh_value"}

        cached_again = await cache.get_or_set("test", "factory_key", factory)
        assert cached_again == {"data": "fresh_value"}

        count = await cache.invalidate_namespace("test")
        assert count > 0

        missing = await cache.get("test", "key1")
        assert missing is None

    @pytest.mark.asyncio
    async def test_concurrent_session_handling(self, init_test_database):
        async def create_project(name, short_id):
            async with init_test_database.session_no_commit() as session:
                uow = UnitOfWork(session=session)
                await uow.__aenter__()
                try:
                    p = await uow.projects.create(name=name, short_id=short_id)
                    return p
                finally:
                    await uow.__aexit__(None, None, None)

        import asyncio
        tasks = [
            create_project(f"Concurrent {i}", f"CON{i:03d}")
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks)
        assert len(results) == 10
        assert all(r is not None for r in results)
        assert len(set(r.uuid for r in results)) == 10
