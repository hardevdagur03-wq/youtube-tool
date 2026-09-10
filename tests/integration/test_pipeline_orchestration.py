from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestPipelineOrchestrationIntegration:
    @pytest.mark.asyncio
    async def test_stage_registration_and_resolution(self):
        from orchestrator.stage_registry import StageRegistry

        registry = StageRegistry()

        @registry.register("metadata", dependencies=[])
        async def metadata_stage(ctx):
            return {"status": "completed"}

        @registry.register("transcript", dependencies=["metadata"])
        async def transcript_stage(ctx):
            return {"status": "completed"}

        assert registry.has("metadata") is True
        assert registry.has("transcript") is True
        assert registry.has("nonexistent") is False

        deps = registry.get_dependencies("transcript")
        assert "metadata" in deps

    @pytest.mark.asyncio
    async def test_dependency_graph_execution(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        await service.update_project(pid, {"status": "running"})
        assert (await service.get_project(pid))["status"] == "running"

        await service.save_video(
            project_uuid=pid, video_id=test_project_data["video_id"],
            title="Dependency Test", channel_title="Test",
        )
        await service.save_transcript(
            project_uuid=pid, video_id=test_project_data["video_id"],
            plain_text="Transcript data.", language="en", source="youtube",
        )
        await service.save_analysis(
            project_uuid=pid, video_id=test_project_data["video_id"],
            summary="Analysis data.", sentiment="positive",
        )

        await service.update_project(pid, {"status": "completed"})
        assert (await service.get_project(pid))["status"] == "completed"

    @pytest.mark.asyncio
    async def test_parallel_stage_execution(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        import asyncio

        async def parallel_save(name):
            return await service.save_video(
                project_uuid=pid, video_id=f"vid-{name}",
                title=f"Parallel {name}", channel_title="Test",
            )

        results = await asyncio.gather(
            parallel_save("A"), parallel_save("B"),
            parallel_save("C"), parallel_save("D"),
        )
        assert len(results) == 4
        assert all(r is not None for r in results)

    @pytest.mark.asyncio
    async def test_conditional_stage_execution(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Conditional Stage Test",
        )
        pid = proj["project_id"]

        settings = test_project_data.get("settings", {})
        if settings.get("seo_enabled", True):
            seo = await service.save_seo(
                project_uuid=pid, primary_keyword="test keyword",
                seo_score=80.0,
            )
            assert seo is not None
        else:
            pass

        target_formats = settings.get("export_formats", ["markdown"])
        for fmt in target_formats:
            export = await service.save_export(
                project_uuid=pid, export_format=fmt,
                filename=f"blog.{fmt}", checksum=f"{fmt}_check",
            )
            assert export is not None

    @pytest.mark.asyncio
    async def test_pipeline_cancellation(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        assert proj["status"] == "created"

        running = await service.update_project(pid, {"status": "running"})
        assert running["status"] == "running"

        cancelled = await service.update_project(pid, {"status": "cancelled"})
        assert cancelled["status"] == "cancelled"

        verify = await service.get_project(pid)
        assert verify["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_pipeline_metrics_collection(self, service, uow, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        start_event = await uow.history.log_event(
            action="pipeline.started",
            entity_type="project", entity_uuid=pid, project_uuid=pid,
        )
        assert start_event is not None

        complete_event = await uow.history.log_event(
            action="pipeline.completed",
            entity_type="project", entity_uuid=pid, project_uuid=pid,
        )
        assert complete_event is not None

        timeline = await uow.history.get_project_timeline(pid)
        assert len(timeline) >= 2
        assert any(e.action == "pipeline.started" for e in timeline)

    @pytest.mark.asyncio
    async def test_pipeline_cache_usage(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        from database.cache import DatabaseCache
        cache = DatabaseCache(use_redis=False)

        await cache.set("pipeline", pid, proj)
        cached_result = await cache.get("pipeline", pid)
        assert cached_result is not None
        assert cached_result["project_id"] == pid

        await cache.invalidate_namespace("pipeline")
        assert await cache.get("pipeline", pid) is None
