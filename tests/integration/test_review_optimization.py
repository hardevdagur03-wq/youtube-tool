from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestReviewOptimizationIntegration:
    @pytest.mark.asyncio
    async def test_review_issues_drive_optimizations(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        review = await service.save_review(
            project_uuid=pid, overall_score=72.5,
            grammar_score=80.0, seo_score=65.0,
            readability_score=70.0,
            issues=[
                {"type": "seo", "severity": "high", "description": "Missing primary keyword in title"},
                {"type": "grammar", "severity": "medium", "description": "Passive voice detected"},
                {"type": "structure", "severity": "low", "description": "Short paragraphs needed"},
            ],
            publication_status="needs_improvement",
        )
        assert review is not None
        assert review["overall_score"] == 72.5
        assert len(review.get("issues", [])) == 3

        optimization = await service.save_optimization(
            project_uuid=pid,
            optimized_content="# Optimized Blog Post\n\nImproved content with SEO keywords.",
            score_improvement=12.5,
            changes_made=[
                {"type": "seo", "description": "Added primary keyword to title"},
                {"type": "grammar", "description": "Reduced passive voice usage"},
                {"type": "structure", "description": "Improved paragraph structure"},
            ],
        )
        assert optimization is not None
        assert optimization["score_improvement"] >= 10.0
        assert len(optimization.get("changes_made", [])) >= 3

    @pytest.mark.asyncio
    async def test_optimization_improves_scores(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        initial_review = await service.save_review(
            project_uuid=pid, overall_score=65.0,
            grammar_score=70.0, seo_score=60.0,
            publication_status="needs_improvement",
        )
        assert initial_review["overall_score"] == 65.0

        optimization = await service.save_optimization(
            project_uuid=pid,
            optimized_content="# Optimized\n\nSEO optimized content with keywords.",
            score_improvement=20.0,
            changes_made=[{"type": "seo", "description": "Keyword optimization"}],
        )
        assert optimization["score_improvement"] == 20.0

        final_review = await service.save_review(
            project_uuid=pid, overall_score=85.0,
            grammar_score=88.0, seo_score=82.0,
            publication_status="approved",
        )
        assert final_review["overall_score"] > initial_review["overall_score"]

    @pytest.mark.asyncio
    async def test_score_changes_across_stages(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        scores = [55.0, 70.0, 82.0, 91.0]
        expected_stages = ["initial", "first_optimization", "second_optimization", "final"]

        for i, score in enumerate(scores):
            review = await service.save_review(
                project_uuid=pid, overall_score=score,
                grammar_score=score, seo_score=score - 5,
                publication_status="in_progress",
            )
            assert review["overall_score"] == score

        final = await service.save_review(
            project_uuid=pid, overall_score=scores[-1],
            grammar_score=scores[-1], seo_score=scores[-1] - 5,
            publication_status="approved",
        )
        assert final["overall_score"] == 91.0
        assert final["overall_score"] > scores[0]

    @pytest.mark.asyncio
    async def test_review_then_optimize_then_review_cycle(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        review1 = await service.save_review(
            project_uuid=pid, overall_score=60.0,
            grammar_score=65.0, seo_score=55.0,
            issues=[{"type": "seo", "severity": "high", "description": "Missing keywords"}],
            publication_status="needs_improvement",
        )

        opt1 = await service.save_optimization(
            project_uuid=pid,
            optimized_content="# Version 2\n\nAdded keyword optimization.",
            score_improvement=15.0,
            changes_made=[{"type": "seo", "description": "Added keywords"}],
        )

        review2 = await service.save_review(
            project_uuid=pid, overall_score=75.0,
            grammar_score=78.0, seo_score=72.0,
            issues=[{"type": "grammar", "severity": "low", "description": "Minor grammar issues"}],
            publication_status="needs_improvement",
        )

        opt2 = await service.save_optimization(
            project_uuid=pid,
            optimized_content="# Version 3\n\nFixed grammar and improved flow.",
            score_improvement=10.0,
            changes_made=[{"type": "grammar", "description": "Fixed grammar"}],
        )

        review3 = await service.save_review(
            project_uuid=pid, overall_score=88.0,
            grammar_score=90.0, seo_score=85.0,
            issues=[],
            publication_status="approved",
        )

        assert review1["overall_score"] < review2["overall_score"] < review3["overall_score"]
        assert opt1["score_improvement"] > 0
        assert opt2["score_improvement"] > 0
        assert review3["publication_status"] == "approved"
