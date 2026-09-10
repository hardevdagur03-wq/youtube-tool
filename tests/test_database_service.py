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
from database.db_service import DatabaseService
from database.session import DatabaseSessionManager


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest_asyncio.fixture
async def service(db_path):
    mgr = DatabaseSessionManager._make_fresh()
    config = DatabaseConfig.for_testing(sqlite_path=db_path)
    mgr.initialize(config)
    await mgr.create_all()
    svc = DatabaseService(session_manager=mgr)
    yield svc
    await mgr.close()


class TestDatabaseServiceProjectCRUD:
    async def test_create_project(self, service):
        proj = await service.create_project(
            url="https://youtube.com/watch?v=abc123",
            video_id="abc123",
            name="Test Project",
        )
        assert proj["project_id"] is not None
        assert proj["name"] == "Test Project"
        assert proj["video_id"] == "abc123"
        assert proj["status"] == "created"

    async def test_get_project(self, service):
        created = await service.create_project(video_id="vid1")
        fetched = await service.get_project(created["project_id"])
        assert fetched is not None
        assert fetched["project_id"] == created["project_id"]
        assert fetched["name"] == created["name"]

    async def test_get_project_not_found(self, service):
        result = await service.get_project("nonexistent")
        assert result is None

    async def test_update_project(self, service):
        created = await service.create_project(name="Original")
        updated = await service.update_project(
            created["project_id"], {"name": "Updated", "status": "running"}
        )
        assert updated is not None
        assert updated["name"] == "Updated"
        assert updated["status"] == "running"

    async def test_delete_project_soft(self, service):
        created = await service.create_project(video_id="del1")
        result = await service.delete_project(created["project_id"], permanent=False)
        assert result is True
        fetched = await service.get_project(created["project_id"])
        assert fetched is None

    async def test_delete_project_hard(self, service):
        created = await service.create_project(video_id="del2")
        result = await service.delete_project(created["project_id"], permanent=True)
        assert result is True
        fetched = await service.get_project(created["project_id"])
        assert fetched is None

    async def test_list_projects(self, service):
        await service.create_project(name="A", video_id="a")
        await service.create_project(name="B", video_id="b")
        await service.create_project(name="C", video_id="c")
        projects = await service.list_projects(limit=10, offset=0)
        assert len(projects) >= 3

    async def test_search_projects(self, service):
        await service.create_project(name="Alpha Project", video_id="alpha123")
        await service.create_project(name="Beta Project", video_id="beta456")
        results = await service.search_projects("Alpha", limit=10)
        assert len(results) >= 1
        assert any("Alpha" in r["name"] for r in results)

    async def test_find_or_create_by_video_existing(self, service):
        created = await service.create_project(video_id="existing_vid")
        found = await service.find_or_create_by_video("existing_vid")
        assert found["project_id"] == created["project_id"]

    async def test_find_or_create_by_video_new(self, service):
        result = await service.find_or_create_by_video("new_vid", url="http://example.com")
        assert result["video_id"] == "new_vid"
        assert result["project_id"] is not None

    async def test_get_summary(self, service):
        created = await service.create_project(
            name="Summary Test", video_id="sum1"
        )
        summary = await service.get_summary(created["project_id"])
        assert summary is not None
        assert summary["name"] == "Summary Test"
        assert "project_id" in summary
        assert "status" in summary

    async def test_get_project_stats(self, service):
        await service.create_project(video_id="s1")
        await service.create_project(video_id="s2")
        stats = await service.get_project_stats()
        assert stats["total_projects"] >= 2

    async def test_project_exists(self, service):
        created = await service.create_project(video_id="exist1")
        assert await service.project_exists(created["project_id"]) is True
        assert await service.project_exists("nonexistent") is False


class TestDatabaseServicePipelineStages:
    async def test_stage_started(self, service):
        proj = await service.create_project(video_id="ps1")
        await service.stage_started(proj["project_id"], "transcript")
        state = await service.get_pipeline_state(proj["project_id"])
        assert state["stages"]["transcript"]["status"] == "running"

    async def test_stage_completed(self, service):
        proj = await service.create_project(video_id="ps2")
        await service.stage_started(proj["project_id"], "transcript")
        await service.stage_completed(proj["project_id"], "transcript")
        state = await service.get_pipeline_state(proj["project_id"])
        assert state["stages"]["transcript"]["status"] == "completed"
        assert state["stages"]["transcript"]["progress_pct"] == 100.0

    async def test_stage_failed(self, service):
        proj = await service.create_project(video_id="ps3")
        await service.stage_started(proj["project_id"], "analysis")
        await service.stage_failed(proj["project_id"], "analysis", "Something broke")
        state = await service.get_pipeline_state(proj["project_id"])
        assert state["stages"]["analysis"]["status"] == "failed"
        assert state["stages"]["analysis"]["error"] == "Something broke"

    async def test_complete_project(self, service):
        proj = await service.create_project(video_id="complete1")
        result = await service.complete_project(proj["project_id"])
        assert result is True
        fetched = await service.get_project(proj["project_id"])
        assert fetched["status"] == "completed"
        assert fetched["completed_at"] is not None

    async def test_pause_resume_project(self, service):
        proj = await service.create_project(video_id="pause1")
        paused = await service.pause_project(proj["project_id"])
        assert paused is True
        state = await service.get_pipeline_state(proj["project_id"])
        assert state["is_paused"] is True

        resumed = await service.resume_project(proj["project_id"])
        assert resumed is not None
        state = await service.get_pipeline_state(proj["project_id"])
        assert state["is_paused"] is False

    async def test_cancel_project(self, service):
        proj = await service.create_project(video_id="cancel1")
        result = await service.cancel_project(proj["project_id"])
        assert result is True
        fetched = await service.get_project(proj["project_id"])
        assert fetched["status"] == "cancelled"


class TestDatabaseServiceStageData:
    async def test_store_and_load_stage_data_json(self, service):
        proj = await service.create_project(video_id="sd1")
        data = {"key": "value", "number": 42}
        await service.store_stage_data(proj["project_id"], "custom_stage", data)
        loaded = await service.load_stage_data(proj["project_id"], "custom_stage")
        assert loaded == data

    async def test_store_and_load_video(self, service):
        proj = await service.create_project(video_id="vid_store")
        video_data = {"title": "My Video", "duration_seconds": 300, "view_count": 1000}
        saved = await service.save_video(proj["project_id"], video_data)
        assert saved.get("title") == "My Video"

        loaded = await service.get_video(proj["project_id"])
        assert loaded is not None
        assert loaded.get("title") == "My Video"

    async def test_store_and_load_transcript(self, service):
        proj = await service.create_project(video_id="trans_store")
        data = {"content": "Hello world", "language": "en", "segment_count": 5}
        saved = await service.save_transcript(proj["project_id"], data)
        assert saved.get("raw_data", {}).get("content") == "Hello world"

        loaded = await service.get_transcript(proj["project_id"])
        assert loaded is not None

    async def test_store_and_load_analysis(self, service):
        proj = await service.create_project(video_id="analysis_store")
        data = {"summary": "Great video", "key_topics": ["python", "coding"], "score": 0.95}
        saved = await service.save_analysis(proj["project_id"], data)
        assert saved["summary"] == "Great video"

        loaded = await service.get_analysis(proj["project_id"])
        assert loaded is not None
        assert loaded["summary"] == "Great video"

    async def test_store_and_load_knowledge_graph(self, service):
        proj = await service.create_project(video_id="kg_store")
        data = {"entities": [{"name": "Python", "type": "language"}], "relationships": []}
        saved = await service.save_knowledge_graph(proj["project_id"], data)
        assert saved is not None

        loaded = await service.get_knowledge_graph(proj["project_id"])
        assert loaded is not None
        assert "entities" in loaded

    async def test_store_and_load_seo(self, service):
        proj = await service.create_project(video_id="seo_store")
        data = {"seo_score": 85, "keywords": ["python", "tutorial"], "meta_description": "Best tutorial"}
        saved = await service.save_seo(proj["project_id"], data)
        assert saved.get("raw_data", {}).get("seo_score") == 85

        loaded = await service.get_seo(proj["project_id"])
        assert loaded is not None

    async def test_store_and_load_outline(self, service):
        proj = await service.create_project(video_id="outline_store")
        data = {"title": {"primary_title": "My Post", "seo_title": "My SEO Post"}, "sections": []}
        saved = await service.save_outline(proj["project_id"], data)
        assert saved is not None

        loaded = await service.get_outline(proj["project_id"])
        assert loaded is not None

    async def test_store_and_load_sections(self, service):
        proj = await service.create_project(video_id="sec_store")
        sections = [
            {"heading": "Introduction", "content": "Intro content", "order": 1},
            {"heading": "Body", "content": "Body content", "order": 2},
        ]
        saved = await service.save_sections(proj["project_id"], sections)
        assert len(saved) == 2

        loaded = await service.get_sections(proj["project_id"])
        assert len(loaded) == 2

    async def test_store_and_load_draft(self, service):
        proj = await service.create_project(video_id="draft_store")
        data = {"markdown_content": "# Hello", "word_count": 10, "section_count": 1}
        saved = await service.save_draft(proj["project_id"], data)
        assert saved is not None
        assert saved["draft_number"] >= 1
        assert saved.get("markdown_content") == "# Hello"

        loaded = await service.get_draft(proj["project_id"])
        assert loaded is not None
        assert loaded.get("markdown_content") == "# Hello"

    async def test_store_and_load_review(self, service):
        proj = await service.create_project(video_id="review_store")
        data = {"score": 92, "status": "approved", "issues": []}
        saved = await service.save_review(proj["project_id"], data)
        assert saved.get("raw_data", {}).get("score") == 92

        loaded = await service.get_review(proj["project_id"])
        assert loaded is not None

    async def test_store_and_load_optimization(self, service):
        proj = await service.create_project(video_id="opt_store")
        data = {"optimization_round": 1, "changes": ["improved readability"], "score_before": 70, "score_after": 90}
        saved = await service.save_optimization(proj["project_id"], data)
        assert saved is not None

        loaded = await service.get_optimization(proj["project_id"])
        assert loaded is not None

    async def test_store_and_load_export(self, service):
        proj = await service.create_project(video_id="export_store")
        data = {"format": "markdown", "file_path": "/tmp/export.md", "file_size": 1024}
        saved = await service.save_export(proj["project_id"], data)
        assert saved.get("raw_data", {}).get("format") == "markdown"

        loaded = await service.get_export(proj["project_id"])
        assert loaded is not None

    async def test_store_stage_data_routes_to_dedicated_table(self, service):
        proj = await service.create_project(video_id="route1")
        await service.store_stage_data(
            proj["project_id"], "transcript",
            {"content": "Routed transcript", "language": "en"},
        )
        loaded = await service.load_stage_data(proj["project_id"], "transcript")
        assert loaded is not None
        assert loaded.get("raw_data", {}).get("content") == "Routed transcript"

    async def test_stage_data_routes_to_json_fallback(self, service):
        proj = await service.create_project(video_id="route2")
        custom = {"foo": "bar", "nested": {"a": 1}}
        await service.store_stage_data(proj["project_id"], "unknown_stage", custom)
        loaded = await service.load_stage_data(proj["project_id"], "unknown_stage")
        assert loaded == custom

    async def test_update_stage_data(self, service):
        proj = await service.create_project(video_id="usd1")
        await service.update_stage_data(proj["project_id"], "custom_stage", {"views": 500})
        data = await service.load_stage_data(proj["project_id"], "custom_stage")
        assert data == {"views": 500}


class TestDatabaseServicePipelineState:
    async def test_save_and_get_pipeline_state(self, service):
        proj = await service.create_project(video_id="pipe1")
        state = {"current_stage": "transcript", "stages": {"metadata": "completed"}}
        saved = await service.save_pipeline_state(proj["project_id"], state)
        assert saved["current_stage"] == "transcript"

        loaded = await service.get_pipeline_state(proj["project_id"])
        assert loaded is not None
        assert loaded["current_stage"] == "transcript"


class TestDatabaseServiceAudit:
    async def test_log_and_get_audit_trail(self, service):
        proj = await service.create_project(video_id="audit1")
        await service.log_event(
            proj["project_id"], "test.event", extra_data={"detail": "hello"}
        )
        trail = await service.get_audit_trail(proj["project_id"], limit=10)
        assert len(trail) >= 1
        assert any(e["action"] == "test.event" for e in trail)


class TestDatabaseServiceVersion:
    async def test_create_and_list_versions(self, service):
        proj = await service.create_project(video_id="ver1")
        vnum = await service.create_version(
            entity_type="project",
            entity_uuid=proj["project_id"],
            project_uuid=proj["project_id"],
            snapshot={"name": "v1", "status": "created"},
            changed_fields=["name"],
        )
        assert vnum == 1

        vnum2 = await service.create_version(
            entity_type="project",
            entity_uuid=proj["project_id"],
            project_uuid=proj["project_id"],
            snapshot={"name": "v2", "status": "running"},
            changed_fields=["status"],
        )
        assert vnum2 == 2

        versions = await service.list_versions("project", proj["project_id"])
        assert len(versions) >= 2


class TestDatabaseServiceHealth:
    async def test_health_check(self, service):
        health = await service.health_check()
        assert health["healthy"] is True
        assert "project_count" in health
        assert "driver" in health

    async def test_health_check_with_data(self, service):
        await service.create_project(video_id="h1")
        await service.create_project(video_id="h2")
        health = await service.health_check()
        assert health["healthy"] is True
        assert health["project_count"] >= 2


class TestDatabaseServiceTransaction:
    async def test_transaction_context_manager(self, service):
        async with service.transaction() as uow:
            p = await uow.projects.create(
                name="Tx Project", short_id="TXP1", video_id="tx1"
            )
            assert p.uuid is not None
            assert p.name == "Tx Project"

        proj = await service.get_project(p.uuid)
        assert proj is not None
        assert proj["name"] == "Tx Project"

    async def test_transaction_rollback_on_failure(self, service):
        with pytest.raises(ValueError):
            async with service.transaction() as uow:
                p = await uow.projects.create(
                    name="Will Rollback", short_id="RB1", video_id="rb1"
                )
                raise ValueError("Force rollback")

        result = await service.get_project(p.uuid)
        assert result is None


class TestDatabaseServiceEdgeCases:
    async def test_operations_on_nonexistent_project(self, service):
        await service.stage_started("nonexistent", "test")
        await service.stage_completed("nonexistent", "test")
        await service.stage_failed("nonexistent", "test", "error")
        result = await service.complete_project("nonexistent")
        assert result is False
        result = await service.pause_project("nonexistent")
        assert result is False
        result = await service.cancel_project("nonexistent")
        assert result is False
        assert await service.project_exists("nonexistent") is False

    async def test_repeated_operations(self, service):
        proj = await service.create_project(video_id="repeat1")
        for i in range(5):
            await service.stage_started(proj["project_id"], "test")
            await service.stage_completed(proj["project_id"], "test")
        state = await service.get_pipeline_state(proj["project_id"])
        assert state["stages"]["test"]["status"] == "completed"

    async def test_store_empty_data(self, service):
        proj = await service.create_project(video_id="empty1")
        await service.store_stage_data(proj["project_id"], "empty_stage", {})
        loaded = await service.load_stage_data(proj["project_id"], "empty_stage")
        assert loaded == {}

    async def test_get_video_not_found(self, service):
        result = await service.get_video("nonexistent")
        assert result is None

    async def test_get_draft_not_found(self, service):
        result = await service.get_draft("nonexistent")
        assert result is None

    async def test_get_sections_empty(self, service):
        result = await service.get_sections("nonexistent")
        assert result == []
