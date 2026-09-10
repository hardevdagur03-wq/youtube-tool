from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestSEORegression:
    @pytest.mark.asyncio
    async def test_seo_score_stability(self, service, test_project_data, regression_engine):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="SEO Stability",
        )
        pid = proj["project_id"]

        seo = await service.save_seo(
            project_uuid=pid, primary_keyword="stability test",
            seo_score=85.0, meta_title="Stability Test",
        )
        min_score = regression_engine["thresholds"]["seo_score_min"]
        assert seo["seo_score"] >= min_score, f"SEO score {seo['seo_score']} below minimum {min_score}"

    @pytest.mark.asyncio
    async def test_keyword_consistency(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Keyword Consistency",
        )
        pid = proj["project_id"]

        seo1 = await service.save_seo(
            project_uuid=pid, primary_keyword="consistent keyword",
            secondary_keywords=["kw1", "kw2", "kw3"],
            seo_score=80.0,
        )

        seo2 = await service.save_seo(
            project_uuid=pid, primary_keyword="consistent keyword",
            secondary_keywords=["kw1", "kw2", "kw3"],
            seo_score=82.0,
        )

        assert seo1["primary_keyword"] == seo2["primary_keyword"]
        assert seo1.get("secondary_keywords") == seo2.get("secondary_keywords")

    @pytest.mark.asyncio
    async def test_meta_tag_consistency(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Meta Tag Consistency",
        )
        pid = proj["project_id"]

        seo = await service.save_seo(
            project_uuid=pid, primary_keyword="meta tags",
            seo_score=88.0,
            meta_title="Meta Tag Guide",
            meta_description="A comprehensive guide to meta tags for SEO.",
        )
        assert seo is not None
        assert len(seo.get("meta_title", "")) > 0
        assert len(seo.get("meta_description", "")) > 0

    @pytest.mark.asyncio
    async def test_seo_score_above_minimum(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="SEO Minimum Check",
        )
        pid = proj["project_id"]

        scores = [75.0, 82.0, 88.0, 91.0, 79.0]
        for score in scores:
            seo = await service.save_seo(
                project_uuid=pid, primary_keyword=f"score-{score}",
                seo_score=score,
            )
            assert seo["seo_score"] >= 70.0, f"Score {score} below 70.0 threshold"

    @pytest.mark.asyncio
    async def test_meta_description_presence(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Meta Description Check",
        )
        pid = proj["project_id"]

        seo = await service.save_seo(
            project_uuid=pid, primary_keyword="meta presence",
            seo_score=90.0,
            meta_description="This is a required meta description field for SEO purposes.",
        )
        assert seo is not None
        meta_desc = seo.get("meta_description", "")
        assert len(meta_desc) > 0
        assert len(meta_desc) >= 10
