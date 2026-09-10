from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestReviewOptimizeBlogE2E:
    @pytest.mark.asyncio
    async def test_get_review_for_blog(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Review Blog",
        )
        pid = proj["project_id"]

        review = await service.save_review(
            project_uuid=pid, overall_score=82.5,
            grammar_score=85.0, seo_score=80.0,
            readability_score=78.0,
            issues=[
                {"type": "seo", "severity": "medium", "description": "Keyword density low"},
                {"type": "grammar", "severity": "low", "description": "Minor punctuation issues"},
            ],
            publication_status="needs_review",
        )
        assert review is not None
        assert review["overall_score"] > 0
        assert len(review.get("issues", [])) == 2

    @pytest.mark.asyncio
    async def test_optimize_based_on_review(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Optimize Blog",
        )
        pid = proj["project_id"]

        review = await service.save_review(
            project_uuid=pid, overall_score=70.0,
            grammar_score=75.0, seo_score=65.0,
            issues=[{"type": "seo", "severity": "high", "description": "Missing meta description"}],
            publication_status="needs_improvement",
        )
        assert review["overall_score"] == 70.0

        optimization = await service.save_optimization(
            project_uuid=pid,
            optimized_content="# Optimized Blog\n\nImproved content with proper SEO structure and meta tags.",
            score_improvement=18.0,
            changes_made=[
                {"type": "seo", "description": "Added meta description"},
                {"type": "structure", "description": "Improved heading hierarchy"},
            ],
        )
        assert optimization is not None
        assert optimization["score_improvement"] > 0

    @pytest.mark.asyncio
    async def test_review_after_optimization_shows_improvement(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Improvement Tracking",
        )
        pid = proj["project_id"]

        initial = await service.save_review(
            project_uuid=pid, overall_score=65.0,
            grammar_score=70.0, seo_score=60.0,
            publication_status="needs_improvement",
        )

        await service.save_optimization(
            project_uuid=pid,
            optimized_content="# Improved\n\nBetter content with SEO.",
            score_improvement=20.0,
            changes_made=[{"type": "seo", "description": "Major SEO overhaul"}],
        )

        final = await service.save_review(
            project_uuid=pid, overall_score=88.0,
            grammar_score=90.0, seo_score=85.0,
            publication_status="approved",
        )
        assert final["overall_score"] > initial["overall_score"]
        assert final["seo_score"] > initial["seo_score"]

    @pytest.mark.asyncio
    async def test_review_edge_cases(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Edge Case Review",
        )
        pid = proj["project_id"]

        perfect = await service.save_review(
            project_uuid=pid, overall_score=100.0,
            grammar_score=100.0, seo_score=100.0,
            issues=[], publication_status="approved",
        )
        assert perfect["overall_score"] == 100.0
        assert perfect["publication_status"] == "approved"

        zero = await service.save_review(
            project_uuid=pid, overall_score=0.0,
            grammar_score=0.0, seo_score=0.0,
            issues=[{"type": "critical", "severity": "high", "description": "No content"}],
            publication_status="rejected",
        )
        assert zero["overall_score"] == 0.0
        assert zero["publication_status"] == "rejected"
