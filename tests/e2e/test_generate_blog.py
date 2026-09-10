from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestGenerateBlogE2E:
    @pytest.mark.asyncio
    async def test_generate_blog_full_pipeline(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Full Blog Generation",
        )
        pid = proj["project_id"]

        await service.save_video(
            project_uuid=pid, video_id=test_project_data["video_id"],
            title="Blog Test Video", channel_title="Test Channel",
        )

        await service.save_transcript(
            project_uuid=pid, video_id=test_project_data["video_id"],
            plain_text="Blog generation test transcript with sufficient content for generation.",
            language="en", source="youtube",
        )

        await service.save_analysis(
            project_uuid=pid, video_id=test_project_data["video_id"],
            summary="Analysis for blog generation.",
            sentiment="positive",
        )

        await service.save_seo(
            project_uuid=pid, primary_keyword="blog generation",
            seo_score=85.0,
        )

        await service.save_outline(
            project_uuid=pid, title="Generated Blog Outline",
            sections=[{"heading": "Intro"}, {"heading": "Body"}, {"heading": "Conclusion"}],
        )

        draft = await service.save_draft(
            project_uuid=pid, draft_number=1,
            markdown_content="# Generated Blog\n\nThis is the fully generated blog content.",
            word_count=15,
        )
        assert draft is not None
        assert draft["word_count"] > 0

    @pytest.mark.asyncio
    async def test_generate_blog_with_options(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Blog With Options",
        )
        pid = proj["project_id"]

        draft = await service.save_draft(
            project_uuid=pid, draft_number=1,
            markdown_content="# Blog With Options\n\nCustomized blog content.",
            word_count=10,
        )

        review = await service.save_review(
            project_uuid=pid, overall_score=90.0,
            grammar_score=92.0, seo_score=88.0,
            publication_status="approved",
        )
        assert review["publication_status"] == "approved"

    @pytest.mark.asyncio
    async def test_generate_blog_tracks_progress(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Progress Tracking Blog",
        )
        pid = proj["project_id"]

        stages = ["metadata", "transcript", "analysis", "seo", "outline", "draft"]
        for i, stage in enumerate(stages):
            updated = await service.update_project(pid, {
                "status": "running" if i < len(stages) - 1 else "completed",
                "current_stage": stage,
            })
            assert updated["status"] in ("running", "completed")

        final = await service.get_project(pid)
        assert final["status"] == "completed"

    @pytest.mark.asyncio
    async def test_generate_blog_handles_errors(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Error Handling Blog",
        )
        pid = proj["project_id"]

        failed = await service.update_project(pid, {
            "status": "failed",
            "error_message": "Blog generation failed: LLM provider error",
        })
        assert failed["status"] == "failed"
        assert "LLM provider error" in failed.get("error_message", "")

    @pytest.mark.asyncio
    async def test_generate_blog_returns_complete_result(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Complete Result Blog",
        )
        pid = proj["project_id"]

        await service.save_video(
            project_uuid=pid, video_id=test_project_data["video_id"],
            title="Complete Video", channel_title="Test",
        )
        await service.save_transcript(
            project_uuid=pid, video_id=test_project_data["video_id"],
            plain_text="Complete transcript for generation.",
            language="en", source="youtube",
        )
        await service.save_analysis(
            project_uuid=pid, video_id=test_project_data["video_id"],
            summary="Complete analysis.", sentiment="positive",
        )
        await service.save_seo(
            project_uuid=pid, primary_keyword="complete blog",
            seo_score=95.0,
        )
        await service.save_outline(
            project_uuid=pid, title="Complete Outline",
            sections=[{"heading": "H1"}, {"heading": "H2"}, {"heading": "H3"}],
        )
        draft = await service.save_draft(
            project_uuid=pid, draft_number=1,
            markdown_content="# Complete Blog\n\nFully generated blog post with all sections.",
            word_count=20,
        )
        review = await service.save_review(
            project_uuid=pid, overall_score=95.0,
            grammar_score=96.0, seo_score=94.0,
            publication_status="approved",
        )

        assert draft is not None
        assert review["overall_score"] >= 90.0
        assert review["publication_status"] == "approved"

        final = await service.get_project(pid)
        assert final is not None
