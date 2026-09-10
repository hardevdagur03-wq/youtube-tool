from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.base import Base
from database.config import DatabaseConfig
from database.models import *
from database.repositories import *
from database.session import DatabaseSessionManager
from database.unit_of_work import UnitOfWork
from database.version_manager import VersionManager
from database.rollback_engine import RollbackEngine
from database.resume_engine import ResumeEngine
from database.audit import AuditService
from database.search import FullTextSearch
from database.cache import DatabaseCache


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest_asyncio.fixture
async def db_manager(db_path):
    mgr = DatabaseSessionManager._make_fresh()
    config = DatabaseConfig.for_testing(sqlite_path=db_path)
    mgr.initialize(config)
    await mgr.create_all()
    yield mgr
    await mgr.close()


@pytest_asyncio.fixture
async def uow(db_manager):
    session = db_manager.session_factory()
    uow_obj = UnitOfWork(session=session)
    await uow_obj.__aenter__()
    try:
        yield uow_obj
    except Exception:
        await uow_obj.__aexit__(*sys.exc_info())
        raise
    else:
        await uow_obj.__aexit__(None, None, None)
    finally:
        await session.close()


class TestProjectRepository:
    async def test_create_project(self, uow):
        p = await uow.projects.create(
            name="Test Project",
            short_id="TP001",
            video_id="abc123",
            status="CREATED",
            language="en",
        )
        assert p.uuid is not None
        assert p.name == "Test Project"
        assert p.status == "CREATED"

    async def test_get_by_uuid(self, uow):
        p = await uow.projects.create(name="Get Test", short_id="GT001")
        retrieved = await uow.projects.get_by_uuid(p.uuid)
        assert retrieved is not None
        assert retrieved.uuid == p.uuid

    async def test_update_project(self, uow):
        p = await uow.projects.create(name="Update Test", short_id="UT001")
        updated = await uow.projects.update(p.uuid, name="Updated Name")
        assert updated is not None
        assert updated.name == "Updated Name"

    async def test_soft_delete(self, uow):
        p = await uow.projects.create(name="Delete Test", short_id="DT001")
        deleted = await uow.projects.soft_delete(p.uuid)
        assert deleted is True
        retrieved = await uow.projects.get_by_uuid(p.uuid)
        assert retrieved is None

    async def test_pagination(self, uow):
        for i in range(25):
            await uow.projects.create(
                name=f"Project {i}", short_id=f"P{i:03d}"
            )
        page = await uow.projects.paginate(page=1, page_size=10)
        assert len(page.items) == 10
        assert page.total >= 25
        assert page.total_pages >= 3

    async def test_search(self, uow):
        await uow.projects.create(name="Python Tutorial", short_id="PT001")
        await uow.projects.create(name="JavaScript Guide", short_id="JG001")
        results = await uow.projects.paginate(
            search_text="Python", search_columns=["name"]
        )
        assert results.total == 1
        assert results.items[0].name == "Python Tutorial"

    async def test_stats(self, uow):
        await uow.projects.create(name="S1", short_id="S001", status="COMPLETED")
        await uow.projects.create(name="S2", short_id="S002", status="COMPLETED")
        await uow.projects.create(name="S3", short_id="S003", status="FAILED")
        stats = await uow.projects.get_project_stats()
        assert stats["total_projects"] >= 3
        assert stats["by_status"]["COMPLETED"] >= 2


class TestVideoRepository:
    async def test_create_video(self, uow):
        v = await uow.videos.create(
            project_uuid="proj-1", video_id="vid-1",
            title="Test Video", channel_title="Test Channel",
        )
        assert v.uuid is not None
        assert v.title == "Test Video"

    async def test_get_by_video_id(self, uow):
        await uow.videos.create(
            project_uuid="proj-2", video_id="vid-unique",
            title="Unique Video",
        )
        v = await uow.videos.get_by_video_id("vid-unique")
        assert v is not None
        assert v.title == "Unique Video"


class TestTranscriptRepository:
    async def test_create_transcript(self, uow):
        t = await uow.transcripts.create(
            project_uuid="proj-1", video_id="vid-1",
            plain_text="Hello world", language="en",
            source="youtube", word_count=2,
        )
        assert t.uuid is not None

    async def test_get_by_project(self, uow):
        await uow.transcripts.create(
            project_uuid="proj-x", video_id="vid-x",
            plain_text="Test", language="en", source="manual",
        )
        t = await uow.transcripts.get_by_project("proj-x")
        assert t is not None
        assert t.plain_text == "Test"

    async def test_search_transcripts(self, uow):
        await uow.transcripts.create(
            project_uuid="proj-s", video_id="vid-s",
            plain_text="Machine learning is fascinating",
            language="en", source="youtube",
        )
        results = await uow.transcripts.search_transcripts("machine")
        assert len(results) >= 1


class TestAnalysisRepository:
    async def test_create_analysis(self, uow):
        a = await uow.analyses.create(
            project_uuid="proj-1", video_id="vid-1",
            summary="Test analysis", sentiment="positive",
        )
        assert a.uuid is not None
        fetched = await uow.analyses.get_by_project("proj-1")
        assert fetched is not None
        assert fetched.summary == "Test analysis"


class TestKnowledgeGraphRepository:
    async def test_create_kg(self, uow):
        kg = await uow.knowledge_graphs.create(
            project_uuid="proj-1", video_id="vid-1",
            entities=[{"name": "AI", "type": "technology"}],
            relationships=[{"source": "AI", "target": "ML", "type": "related"}],
        )
        assert kg.uuid is not None
        assert len(kg.entities) == 1


class TestSEORepository:
    async def test_create_seo(self, uow):
        s = await uow.seo.create(
            project_uuid="proj-1",
            primary_keyword="machine learning",
            meta_title="ML Guide",
            seo_score=85.0,
        )
        assert s.uuid is not None
        assert s.primary_keyword == "machine learning"


class TestOutlineRepository:
    async def test_create_outline(self, uow):
        o = await uow.outlines.create(
            project_uuid="proj-1",
            title="Blog Outline",
            sections=[{"heading": "Intro"}, {"heading": "Body"}],
        )
        assert o.uuid is not None
        assert o.title == "Blog Outline"


class TestSectionRepository:
    async def test_create_section(self, uow):
        s = await uow.sections.create(
            project_uuid="proj-1",
            heading="Introduction",
            content="This is the intro.",
            order=0,
        )
        assert s.uuid is not None
        assert s.heading == "Introduction"

    async def test_list_by_project(self, uow):
        await uow.sections.create(project_uuid="proj-list", heading="S1", order=0)
        await uow.sections.create(project_uuid="proj-list", heading="S2", order=1)
        sections = await uow.sections.list_by_project("proj-list")
        assert len(sections) == 2


class TestDraftRepository:
    async def test_create_draft(self, uow):
        d = await uow.drafts.create(
            project_uuid="proj-1",
            draft_number=1,
            markdown_content="# Hello",
            word_count=2,
        )
        assert d.uuid is not None
        assert d.draft_number == 1

    async def test_get_latest(self, uow):
        await uow.drafts.create(project_uuid="proj-latest", draft_number=1)
        await uow.drafts.create(project_uuid="proj-latest", draft_number=2)
        latest = await uow.drafts.get_latest_by_project("proj-latest")
        assert latest is not None
        assert latest.draft_number == 2


class TestReviewRepository:
    async def test_create_review(self, uow):
        r = await uow.reviews.create(
            project_uuid="proj-1",
            overall_score=92.5,
            grammar_score=95.0,
            seo_score=88.0,
            publication_status="approved",
        )
        assert r.uuid is not None
        assert r.overall_score == 92.5


class TestExportRepository:
    async def test_create_export(self, uow):
        e = await uow.exports.create(
            project_uuid="proj-1",
            export_format="markdown",
            filename="blog.md",
            checksum="abc123",
        )
        assert e.uuid is not None
        assert e.export_format == "markdown"

    async def test_increment_download(self, uow):
        e = await uow.exports.create(
            project_uuid="proj-dl", export_format="html",
            filename="blog.html", checksum="def456",
        )
        await uow.exports.increment_download_count(e.uuid)
        fetched = await uow.exports.get_by_uuid(e.uuid)
        assert fetched is not None
        assert fetched.download_count == 1


class TestHistoryRepository:
    async def test_log_event(self, uow):
        event = await uow.history.log_event(
            action="project.created",
            entity_type="project",
            entity_uuid="proj-uuid-1",
            project_uuid="proj-uuid-1",
        )
        assert event.uuid is not None
        assert event.action == "project.created"

    async def test_get_timeline(self, uow):
        await uow.history.log_event(
            action="transcript.generated",
            entity_type="transcript",
            entity_uuid="t-uuid-1",
            project_uuid="proj-timeline",
        )
        await uow.history.log_event(
            action="analysis.completed",
            entity_type="analysis",
            entity_uuid="a-uuid-1",
            project_uuid="proj-timeline",
        )
        timeline = await uow.history.get_project_timeline("proj-timeline")
        assert len(timeline) == 2


class TestUnitOfWork:
    async def test_transaction_rollback_on_failure(self, db_manager):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            config = DatabaseConfig.for_testing(sqlite_path=path)
            mgr = DatabaseSessionManager()
            mgr.initialize(config)
            await mgr.create_all()

            try:
                async with UnitOfWork() as u:
                    await u.projects.create(name="Will Rollback", short_id="RB001")
                    raise ValueError("Force rollback")
            except ValueError:
                pass

            async with UnitOfWork() as u:
                projects = await u.projects.list_all()
                assert len(projects) == 0
            await mgr.close()
        finally:
            if os.path.exists(path):
                os.unlink(path)

    async def test_nested_uow_independence(self, db_manager):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            config = DatabaseConfig.for_testing(sqlite_path=path)
            mgr = DatabaseSessionManager()
            mgr.initialize(config)
            await mgr.create_all()

            async with UnitOfWork() as u1:
                await u1.projects.create(name="UOW1 Project", short_id="U1")

            async with UnitOfWork() as u2:
                await u2.projects.create(name="UOW2 Project", short_id="U2")

            async with UnitOfWork() as u:
                all_projects = await u.projects.list_all()
                assert len(all_projects) == 2
            await mgr.close()
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestVersionManager:
    async def test_create_version(self, uow):
        vm = VersionManager(uow)
        v = await vm.create_version(
            entity_type="project",
            entity_uuid="proj-v-1",
            project_uuid="proj-v-1",
            snapshot={"name": "V1", "status": "CREATED"},
            changed_by="test",
        )
        assert v == 1

    async def test_list_versions(self, uow):
        vm = VersionManager(uow)
        await vm.create_version(
            entity_type="project", entity_uuid="proj-v-list",
            project_uuid="proj-v-list",
            snapshot={"name": "V1"},
        )
        await vm.create_version(
            entity_type="project", entity_uuid="proj-v-list",
            project_uuid="proj-v-list",
            snapshot={"name": "V2"},
        )
        versions = await vm.list_versions("project", "proj-v-list")
        assert len(versions) == 2

    async def test_get_version(self, uow):
        vm = VersionManager(uow)
        await vm.create_version(
            entity_type="project", entity_uuid="proj-v-get",
            project_uuid="proj-v-get",
            snapshot={"name": "Snapshot Data"},
        )
        snap = await vm.get_version("project", "proj-v-get", 1)
        assert snap is not None
        assert snap["name"] == "Snapshot Data"


class TestRollbackEngine:
    async def test_rollback_project(self, uow):
        p = await uow.projects.create(
            name="Original", short_id="RB2", status="COMPLETED"
        )
        await uow.projects.update(p.uuid, name="Modified", status="FAILED")

        vm = VersionManager(uow)
        await vm.create_version(
            entity_type="project", entity_uuid=p.uuid,
            project_uuid=p.uuid,
            snapshot={"name": "Original", "status": "COMPLETED"},
            changed_by="test",
        )

        engine = RollbackEngine(uow)
        result = await engine.rollback_project(p.uuid, 1)
        assert result is not None

        restored = await uow.projects.get_by_uuid(p.uuid)
        assert restored.name == "Original"


class TestResumeEngine:
    async def test_get_resume_state(self, uow):
        p = await uow.projects.create(
            name="Resume Test", short_id="RES1", status="FAILED",
            pipeline_state={"current_stage": "analysis", "completed_stages": ["metadata", "transcript"]},
        )
        engine = ResumeEngine(uow)
        state = await engine.get_resume_state(p.uuid)
        assert state["can_resume"] is True
        assert state["current_stage"] == "analysis"

    async def test_mark_stage_completed(self, uow):
        p = await uow.projects.create(
            name="Stage Test", short_id="ST1", status="CREATED",
            pipeline_state={"current_stage": "metadata", "completed_stages": []},
        )
        engine = ResumeEngine(uow)
        await engine.mark_stage_completed(p.uuid, "metadata")
        updated = await uow.projects.get_by_uuid(p.uuid)
        assert "metadata" in updated.pipeline_state.get("completed_stages", [])

    async def test_compute_resume_plan(self, uow):
        p = await uow.projects.create(
            name="Plan Test", short_id="PLAN1", status="FAILED",
            pipeline_state={
                "current_stage": "analysis",
                "completed_stages": ["metadata", "transcript"],
                "failed_stages": [{"stage": "analysis", "error": "LLM timeout"}],
            },
        )
        engine = ResumeEngine(uow)
        plan = await engine.compute_resume_plan(p.uuid)
        assert plan["can_resume"] is True
        assert plan["resume_from"] == "analysis"


class TestAuditService:
    async def test_log_and_retrieve(self, uow):
        audit = AuditService(uow)
        await audit.log_project_event(
            project_uuid="proj-audit",
            action="project.created",
            actor_id="user-1",
        )
        await audit.log_pipeline_event(
            project_uuid="proj-audit",
            action="pipeline.stage_completed",
            stage="transcript",
        )
        history = await audit.get_project_history("proj-audit")
        assert len(history) == 2

    async def test_recent_activity(self, uow):
        audit = AuditService(uow)
        await audit.log_project_event("proj-recent", "project.created")
        activity = await audit.get_recent_activity(limit=10)
        assert len(activity) >= 1


class TestSearch:
    async def test_global_search(self, db_manager):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            config = DatabaseConfig.for_testing(sqlite_path=path)
            mgr = DatabaseSessionManager()
            mgr.initialize(config)
            await mgr.create_all()

            async with UnitOfWork() as u:
                await u.projects.create(
                    name="Python Machine Learning", short_id="PML",
                    description="A comprehensive guide"
                )
                await u.videos.create(
                    project_uuid="proj-s", video_id="vid-s",
                    title="ML Tutorial", channel_title="AI Channel",
                )

            async with mgr.session_no_commit() as session:
                search = FullTextSearch(session)
                results = await search.global_search("Python")
                assert len(results["projects"]) >= 1

            await mgr.close()
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestCache:
    async def test_set_get(self):
        cache = DatabaseCache(use_redis=False)
        await cache.set("test", "key1", {"hello": "world"})
        result = await cache.get("test", "key1")
        assert result == {"hello": "world"}

    async def test_get_or_set(self):
        cache = DatabaseCache(use_redis=False)
        called = False

        async def factory():
            nonlocal called
            called = True
            return {"data": "fresh"}

        result = await cache.get_or_set("test", "factory", factory)
        assert result == {"data": "fresh"}
        assert called is True

        called = False
        result2 = await cache.get_or_set("test", "factory", factory)
        assert result2 == {"data": "fresh"}
        assert called is False

    async def test_invalidate(self):
        cache = DatabaseCache(use_redis=False)
        await cache.set("ns1", "item1", "value1")
        await cache.set("ns1", "item2", "value2")
        await cache.set("ns2", "item1", "value3")
        count = await cache.invalidate_namespace("ns1")
        assert count == 2
        assert await cache.get("ns1", "item1") is None
        assert await cache.get("ns2", "item1") == "value3"


class TestPipelineState:
    async def test_create_pipeline_state(self, uow):
        ps = await uow.projects.create(
            name="Pipeline State Test", short_id="PST1",
            pipeline_state={"current_stage": "created", "completed_stages": []},
        )
        assert ps.pipeline_state["current_stage"] == "created"

    async def test_update_stage_data(self, uow):
        p = await uow.projects.create(name="Stage Data", short_id="SD1")
        updated = await uow.projects.update_stage_data(
            p.uuid, "metadata", {"title": "Test Video", "views": 1000}
        )
        assert updated is not None
        assert updated.stage_data["metadata"]["title"] == "Test Video"


@pytest.mark.skip(reason="Requires PostgreSQL with full-text search setup")
class TestPostgreSQLFeatures:
    pass
