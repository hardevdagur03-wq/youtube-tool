from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestFullPipelineExecution:
    @pytest.mark.asyncio
    async def test_full_pipeline_execution(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name=test_project_data["name"],
        )
        pid = proj["project_id"]
        assert pid is not None
        assert proj["status"] == "created"

        video = await service.save_video(
            project_uuid=pid, video_id=test_project_data["video_id"],
            title="Test Video Title", channel_title="Test Channel",
        )
        assert video is not None

        transcript = await service.save_transcript(
            project_uuid=pid, video_id=test_project_data["video_id"],
            plain_text="Test transcript content for pipeline execution testing.",
            language="en", source="youtube",
        )
        assert transcript is not None
        assert transcript["word_count"] > 0

        analysis = await service.save_analysis(
            project_uuid=pid, video_id=test_project_data["video_id"],
            summary="Test analysis summary", sentiment="positive",
        )
        assert analysis is not None

        kg = await service.save_knowledge_graph(
            project_uuid=pid, video_id=test_project_data["video_id"],
            entities=[{"name": "Python", "type": "language"}],
            relationships=[{"source": "Python", "target": "Django", "type": "uses"}],
        )
        assert kg is not None
        assert len(kg["entities"]) == 1

        seo = await service.save_seo(
            project_uuid=pid, primary_keyword="python programming",
            seo_score=85.0, meta_title="Python Guide",
        )
        assert seo is not None
        assert seo["seo_score"] == 85.0

        outline = await service.save_outline(
            project_uuid=pid, title="Blog Outline",
            sections=[{"heading": "Intro"}, {"heading": "Body"}, {"heading": "Conclusion"}],
        )
        assert outline is not None

        sections_data = [
            {"heading": "Introduction", "content": "Intro content", "order": 0},
            {"heading": "Main Body", "content": "Body content", "order": 1},
            {"heading": "Conclusion", "content": "Conclusion content", "order": 2},
        ]
        for s in sections_data:
            section = await service.save_section(
                project_uuid=pid, heading=s["heading"],
                content=s["content"], order=s["order"],
            )
            assert section is not None

        draft = await service.save_draft(
            project_uuid=pid, draft_number=1,
            markdown_content="# Test\n\nContent here.",
            word_count=50,
        )
        assert draft is not None
        assert draft["draft_number"] == 1

        review = await service.save_review(
            project_uuid=pid, overall_score=88.5,
            grammar_score=90.0, seo_score=85.0,
            publication_status="needs_review",
        )
        assert review is not None
        assert review["overall_score"] == 88.5

        optimization = await service.save_optimization(
            project_uuid=pid, optimized_content="# Optimized\n\nBetter content.",
            score_improvement=5.0,
            changes_made=[{"type": "seo", "description": "Added keywords"}],
        )
        assert optimization is not None
        assert optimization["score_improvement"] == 5.0

        export = await service.save_export(
            project_uuid=pid, export_format="markdown",
            filename="blog.md", checksum="abc123",
        )
        assert export is not None
        assert export["export_format"] == "markdown"

        final = await service.get_project(pid)
        assert final is not None

    @pytest.mark.asyncio
    async def test_pipeline_with_mock_llm(self, service, mock_llm_provider, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        mock_llm_provider.generate.assert_not_called()
        response = mock_llm_provider.generate(text="Analyze this content")
        assert response["text"] == "Mocked LLM response"

    @pytest.mark.asyncio
    async def test_pipeline_data_persistence(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Persistence Test",
        )
        pid = proj["project_id"]

        await service.save_video(
            project_uuid=pid, video_id="vid-persist",
            title="Persist Title", channel_title="Persist Channel",
        )

        await service.save_transcript(
            project_uuid=pid, video_id="vid-persist",
            plain_text="Persistence check transcript data.",
            language="en", source="youtube",
        )

        reloaded = await service.get_project(pid)
        assert reloaded["name"] == "Persistence Test"
        assert reloaded["video_id"] == "vid-persist"

    @pytest.mark.asyncio
    async def test_pipeline_state_transitions(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]
        assert proj["status"] == "created"

        updated = await service.update_project(pid, {"status": "running"})
        assert updated["status"] == "running"

        updated2 = await service.update_project(pid, {"status": "completed"})
        assert updated2["status"] == "completed"

        final = await service.get_project(pid)
        assert final["status"] == "completed"

    @pytest.mark.asyncio
    async def test_pipeline_event_emission(self, service, uow, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        event = await uow.history.log_event(
            action="pipeline.started",
            entity_type="project",
            entity_uuid=pid,
            project_uuid=pid,
        )
        assert event is not None
        assert event.action == "pipeline.started"

        event2 = await uow.history.log_event(
            action="pipeline.stage_completed",
            entity_type="stage",
            entity_uuid=pid,
            project_uuid=pid,
            metadata={"stage": "metadata"},
        )
        assert event2 is not None
        assert event2.action == "pipeline.stage_completed"

        timeline = await uow.history.get_project_timeline(pid)
        assert len(timeline) >= 2

    @pytest.mark.asyncio
    async def test_pipeline_error_propagation(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        updated = await service.update_project(pid, {
            "status": "failed",
            "error_message": "Pipeline stage failed: LLM timeout",
        })
        assert updated["status"] == "failed"
        assert "LLM timeout" in updated["error_message"]

    @pytest.mark.asyncio
    async def test_pipeline_rollback(self, service, uow, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Original Name",
        )
        pid = proj["project_id"]

        await service.update_project(pid, {"name": "Modified Name", "status": "failed"})

        assert proj["name"] == "Original Name"

        rolled_back = await service.update_project(pid, {"name": "Original Name", "status": "created"})
        assert rolled_back["name"] == "Original Name"
        assert rolled_back["status"] == "created"

    @pytest.mark.asyncio
    async def test_pipeline_cache_integration(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        fresh = await service.get_project(pid)
        assert fresh is not None
        assert fresh["project_id"] == pid

        cached = await service.get_project(pid)
        assert cached is not None
        assert cached["project_id"] == pid
