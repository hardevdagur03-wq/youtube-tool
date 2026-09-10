from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestPipelineRegression:
    @pytest.mark.asyncio
    async def test_pipeline_output_consistency(self, service, test_project_data, golden_dataset):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Consistency Run 1",
        )
        pid1 = proj["project_id"]
        await service.save_video(
            project_uuid=pid1, video_id=test_project_data["video_id"],
            title="Consistency Video", channel_title="Test",
        )
        await service.save_transcript(
            project_uuid=pid1, video_id=test_project_data["video_id"],
            plain_text="Consistency test transcript content.", language="en", source="youtube",
        )
        await service.save_analysis(
            project_uuid=pid1, video_id=test_project_data["video_id"],
            summary="Consistency analysis.", sentiment="positive",
        )
        await service.save_seo(
            project_uuid=pid1, primary_keyword="consistency",
            seo_score=85.0,
        )
        await service.save_outline(
            project_uuid=pid1, title="Consistency Outline",
            sections=[{"heading": "Intro"}, {"heading": "Body"}, {"heading": "Conclusion"}],
        )

        proj2 = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Consistency Run 2",
        )
        pid2 = proj2["project_id"]
        await service.save_video(
            project_uuid=pid2, video_id=test_project_data["video_id"],
            title="Consistency Video", channel_title="Test",
        )
        await service.save_transcript(
            project_uuid=pid2, video_id=test_project_data["video_id"],
            plain_text="Consistency test transcript content.", language="en", source="youtube",
        )
        await service.save_analysis(
            project_uuid=pid2, video_id=test_project_data["video_id"],
            summary="Consistency analysis.", sentiment="positive",
        )
        await service.save_seo(
            project_uuid=pid2, primary_keyword="consistency",
            seo_score=85.0,
        )
        await service.save_outline(
            project_uuid=pid2, title="Consistency Outline",
            sections=[{"heading": "Intro"}, {"heading": "Body"}, {"heading": "Conclusion"}],
        )

        p1 = await service.get_project(pid1)
        p2 = await service.get_project(pid2)
        assert p1["video_id"] == p2["video_id"]
        assert p1["name"] != p2["name"]

    @pytest.mark.asyncio
    async def test_pipeline_duration_regression(self, service, test_project_data, baseline_metrics):
        import time

        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Duration Test",
        )
        pid = proj["project_id"]

        start = time.time()
        await service.save_video(
            project_uuid=pid, video_id=test_project_data["video_id"],
            title="Duration Video", channel_title="Test",
        )
        await service.save_transcript(
            project_uuid=pid, video_id=test_project_data["video_id"],
            plain_text="Duration test transcript.", language="en", source="youtube",
        )
        await service.save_analysis(
            project_uuid=pid, video_id=test_project_data["video_id"],
            summary="Duration analysis.", sentiment="positive",
        )
        await service.save_seo(
            project_uuid=pid, primary_keyword="duration",
            seo_score=85.0,
        )
        await service.save_outline(
            project_uuid=pid, title="Duration Outline",
            sections=[{"heading": "A"}, {"heading": "B"}],
        )
        await service.save_draft(
            project_uuid=pid, draft_number=1,
            markdown_content="# Duration Draft\n\nContent.",
            word_count=6,
        )
        elapsed = time.time() - start

        max_duration = baseline_metrics.get("pipeline_duration_seconds", 300)
        assert elapsed < max_duration, f"Pipeline took {elapsed:.2f}s, exceeds {max_duration}s"

    @pytest.mark.asyncio
    async def test_pipeline_stage_regression(self, service, test_project_data, regression_engine):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Stage Regression",
        )
        pid = proj["project_id"]

        stages = ["metadata", "transcript", "analysis", "seo", "outline", "draft"]
        for stage in stages:
            updated = await service.update_project(pid, {
                "current_stage": stage,
                "status": "running",
            })
            assert updated["status"] == "running"

            await service.update_project(pid, {
                "status": "completed" if stage == stages[-1] else "running",
            })

        final = await service.get_project(pid)
        assert final is not None
