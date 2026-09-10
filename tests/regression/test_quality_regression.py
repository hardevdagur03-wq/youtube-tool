from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestQualityRegression:
    @pytest.mark.asyncio
    async def test_readability_stability(self, service, test_project_data, regression_engine):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Readability Check",
        )
        pid = proj["project_id"]

        review = await service.save_review(
            project_uuid=pid, overall_score=80.0,
            readability_score=75.0,
            grammar_score=85.0, seo_score=78.0,
            publication_status="approved",
        )
        min_readability = regression_engine["thresholds"].get("readability_min", 60.0)
        assert review["readability_score"] >= min_readability

    @pytest.mark.asyncio
    async def test_grammar_quality_stability(self, service, test_project_data, regression_engine):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Grammar Stability",
        )
        pid = proj["project_id"]

        review = await service.save_review(
            project_uuid=pid, overall_score=85.0,
            grammar_score=92.0, seo_score=82.0,
            publication_status="approved",
        )
        min_grammar = regression_engine["thresholds"].get("grammar_min", 75.0)
        assert review["grammar_score"] >= min_grammar

    @pytest.mark.asyncio
    async def test_content_length_stability(self, service, test_project_data, regression_engine):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Content Length",
        )
        pid = proj["project_id"]

        draft = await service.save_draft(
            project_uuid=pid, draft_number=1,
            markdown_content="# Stability\n\n" + "Content paragraph. " * 50,
            word_count=100,
        )
        min_words = regression_engine["thresholds"].get("word_count_min", 50)
        assert draft["word_count"] >= min_words

    @pytest.mark.asyncio
    async def test_overall_quality_score_stability(self, service, test_project_data, regression_engine):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Quality Score Stability",
        )
        pid = proj["project_id"]

        review = await service.save_review(
            project_uuid=pid, overall_score=82.0,
            grammar_score=85.0, seo_score=80.0,
            readability_score=78.0,
            publication_status="approved",
        )
        min_quality = regression_engine["thresholds"].get("quality_min", 70.0)
        assert review["overall_score"] >= min_quality

    @pytest.mark.asyncio
    async def test_score_consistency_across_reviews(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Score Consistency",
        )
        pid = proj["project_id"]

        scores = []
        for i in range(5):
            review = await service.save_review(
                project_uuid=pid, overall_score=80.0 + i,
                grammar_score=82.0 + i, seo_score=78.0 + i,
                publication_status="in_progress",
            )
            scores.append(review["overall_score"])

        assert all(75.0 <= s <= 100.0 for s in scores)
        assert scores == sorted(scores)
