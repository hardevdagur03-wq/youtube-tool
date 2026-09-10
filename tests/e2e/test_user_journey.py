from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestUserJourneyE2E:
    @pytest.mark.asyncio
    async def test_full_user_journey(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Full Journey",
        )
        pid = proj["project_id"]
        assert proj["status"] == "created"

        await service.save_video(
            project_uuid=pid, video_id=test_project_data["video_id"],
            title="Journey Video", channel_title="Test Channel",
        )
        await service.save_transcript(
            project_uuid=pid, video_id=test_project_data["video_id"],
            plain_text="Journey transcript content.",
            language="en", source="youtube",
        )
        await service.save_analysis(
            project_uuid=pid, video_id=test_project_data["video_id"],
            summary="Journey analysis.", sentiment="positive",
        )

        review = await service.save_review(
            project_uuid=pid, overall_score=75.0,
            grammar_score=78.0, seo_score=72.0,
            issues=[{"type": "seo", "severity": "medium", "description": "Improve keywords"}],
            publication_status="needs_improvement",
        )
        assert review["overall_score"] > 0

        optimization = await service.save_optimization(
            project_uuid=pid,
            optimized_content="# Optimized Journey\n\nImproved content.",
            score_improvement=15.0,
            changes_made=[{"type": "seo", "description": "Keyword optimization"}],
        )
        assert optimization["score_improvement"] > 0

        draft = await service.save_draft(
            project_uuid=pid, draft_number=1,
            markdown_content="# Final Draft\n\nCompleted blog post content.",
            word_count=12,
        )
        assert draft is not None

        export = await service.save_export(
            project_uuid=pid, export_format="markdown",
            filename="final-blog.md", checksum="final123",
        )
        assert export is not None

        await service.delete_project(pid, permanent=False)
        assert await service.get_project(pid) is None

    @pytest.mark.asyncio
    async def test_multiple_projects_parallel(self, service):
        import asyncio

        async def create_and_process(name, video_id):
            proj = await service.create_project(
                url=f"https://youtube.com/watch?v={video_id}",
                video_id=video_id,
                name=name,
            )
            pid = proj["project_id"]
            await service.save_video(
                project_uuid=pid, video_id=video_id,
                title=f"{name} Video", channel_title="Multi Test",
            )
            await service.save_transcript(
                project_uuid=pid, video_id=video_id,
                plain_text=f"Transcript for {name}.",
                language="en", source="youtube",
            )
            await service.update_project(pid, {"status": "completed"})
            return await service.get_project(pid)

        projects = await asyncio.gather(
            create_and_process("Project A", "vid-a"),
            create_and_process("Project B", "vid-b"),
            create_and_process("Project C", "vid-c"),
            create_and_process("Project D", "vid-d"),
            create_and_process("Project E", "vid-e"),
        )
        assert len(projects) == 5
        assert all(p is not None for p in projects)
        assert all(p["status"] == "completed" for p in projects)

    @pytest.mark.asyncio
    async def test_project_sharing_scenario(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Shared Project",
        )
        pid = proj["project_id"]

        await service.save_video(
            project_uuid=pid, video_id=test_project_data["video_id"],
            title="Shared Video", channel_title="Test",
        )

        export_md = await service.save_export(
            project_uuid=pid, export_format="markdown",
            filename="shared.md", checksum="shared-md",
        )
        export_html = await service.save_export(
            project_uuid=pid, export_format="html",
            filename="shared.html", checksum="shared-html",
        )

        assert export_md is not None
        assert export_html is not None
        assert export_md["export_format"] != export_html["export_format"]

        fetched = await service.get_project(pid)
        assert fetched is not None
        assert fetched["name"] == "Shared Project"
