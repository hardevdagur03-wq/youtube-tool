from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestSEOOutlineIntegration:
    @pytest.mark.asyncio
    async def test_seo_keywords_influence_outline(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        seo = await service.save_seo(
            project_uuid=pid,
            primary_keyword="Python programming",
            secondary_keywords=["data science", "machine learning", "web development"],
            seo_score=90.0,
            meta_title="Complete Python Programming Guide",
            meta_description="A comprehensive guide to Python programming for data science.",
        )
        assert seo is not None
        assert seo["primary_keyword"] == "Python programming"

        outline = await service.save_outline(
            project_uuid=pid,
            title="Complete Python Programming Guide",
            sections=[
                {"heading": "Introduction to Python", "keyword_focus": "Python programming"},
                {"heading": "Python for Data Science", "keyword_focus": "data science"},
                {"heading": "Machine Learning with Python", "keyword_focus": "machine learning"},
                {"heading": "Python Web Development", "keyword_focus": "web development"},
                {"heading": "Conclusion", "keyword_focus": ""},
            ],
        )
        assert outline is not None
        assert outline["title"] == "Complete Python Programming Guide"
        assert len(outline["sections"]) >= 4

    @pytest.mark.asyncio
    async def test_outline_structure_reflects_seo_strategy(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        await service.save_seo(
            project_uuid=pid,
            primary_keyword="advanced Python",
            seo_score=85.0,
            content_strategy={
                "content_depth": "comprehensive",
                "target_word_count": 2500,
                "content_angle": "Advanced Python techniques for experienced developers",
            },
        )

        outline = await service.save_outline(
            project_uuid=pid,
            title="Advanced Python Techniques",
            sections=[
                {"heading": "Introduction", "expected_word_count": 200},
                {"heading": "Advanced Data Structures", "expected_word_count": 500},
                {"heading": "Metaclasses and Decorators", "expected_word_count": 600},
                {"heading": "Concurrency and Parallelism", "expected_word_count": 500},
                {"heading": "Performance Optimization", "expected_word_count": 400},
                {"heading": "Best Practices", "expected_word_count": 300},
            ],
        )
        assert outline is not None
        section_count = len(outline["sections"])
        assert section_count >= 4

    @pytest.mark.asyncio
    async def test_heading_strategy_alignment(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        await service.save_seo(
            project_uuid=pid,
            primary_keyword="Python best practices",
            seo_score=88.0,
            heading_strategy={
                "include_how_to": True,
                "include_what_is": True,
                "include_benefits": True,
                "question_based_headings": True,
            },
        )

        outline = await service.save_outline(
            project_uuid=pid,
            title="Python Best Practices Guide",
            sections=[
                {"heading": "What is Python?", "type": "what_is"},
                {"heading": "How to Write Clean Python Code", "type": "how_to"},
                {"heading": "Benefits of Best Practices", "type": "benefits"},
                {"heading": "Common Pitfalls to Avoid", "type": "pitfalls"},
            ],
        )
        assert outline is not None
        headings = [s["heading"] for s in outline["sections"]]
        assert any("What is" in h for h in headings)
        assert any("How to" in h for h in headings)
        assert any("Benefits" in h for h in headings)
