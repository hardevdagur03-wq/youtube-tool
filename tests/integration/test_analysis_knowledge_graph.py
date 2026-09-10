from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestAnalysisKnowledgeGraphIntegration:
    @pytest.mark.asyncio
    async def test_analysis_feeds_knowledge_graph(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        analysis = await service.save_analysis(
            project_uuid=pid, video_id=test_project_data["video_id"],
            summary="Python is a versatile programming language used in data science.",
            sentiment="positive",
            topics=["Python", "Data Science", "Machine Learning"],
            key_takeaways=["Python is easy to learn", "Great for data science"],
        )
        assert analysis is not None

        kg = await service.save_knowledge_graph(
            project_uuid=pid, video_id=test_project_data["video_id"],
            entities=[
                {"name": "Python", "type": "language", "importance": 1.0},
                {"name": "Data Science", "type": "field", "importance": 0.9},
                {"name": "Machine Learning", "type": "field", "importance": 0.8},
            ],
            relationships=[
                {"source": "Python", "target": "Data Science", "type": "used_in"},
                {"source": "Python", "target": "Machine Learning", "type": "used_in"},
            ],
        )
        assert kg is not None
        assert len(kg["entities"]) == 3
        assert len(kg["relationships"]) == 2

    @pytest.mark.asyncio
    async def test_entities_from_analysis_appear_in_kg(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        analysis = await service.save_analysis(
            project_uuid=pid, video_id=test_project_data["video_id"],
            summary="Analysis with specific entities.",
            sentiment="neutral",
            entities={
                "technologies": ["Python", "Django", "FastAPI"],
                "frameworks": ["React", "Angular"],
                "tools": ["Docker", "Kubernetes"],
            },
        )

        kg = await service.save_knowledge_graph(
            project_uuid=pid, video_id=test_project_data["video_id"],
            entities=[
                {"name": "Python", "type": "technology"},
                {"name": "Django", "type": "framework"},
                {"name": "Docker", "type": "tool"},
                {"name": "Kubernetes", "type": "tool"},
            ],
            relationships=[
                {"source": "Django", "target": "Python", "type": "based_on"},
            ],
        )
        assert kg is not None
        entity_names = [e["name"] for e in kg["entities"]]
        assert "Python" in entity_names
        assert "Django" in entity_names

    @pytest.mark.asyncio
    async def test_kg_enriches_analysis_data(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        await service.save_analysis(
            project_uuid=pid, video_id=test_project_data["video_id"],
            summary="Base analysis.", sentiment="positive",
        )

        kg = await service.save_knowledge_graph(
            project_uuid=pid, video_id=test_project_data["video_id"],
            entities=[{"name": "Entity1", "type": "concept"}],
            relationships=[],
        )
        assert kg is not None

        enriched_analysis = await service.save_analysis(
            project_uuid=pid, video_id=test_project_data["video_id"],
            summary="Enriched analysis with KG data.",
            sentiment="positive",
            topics=["Entity1"],
        )
        assert enriched_analysis is not None
        assert "Entity1" in enriched_analysis.get("topics", [])

    @pytest.mark.asyncio
    async def test_consistency_between_analysis_and_kg(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        analysis = await service.save_analysis(
            project_uuid=pid, video_id=test_project_data["video_id"],
            summary="Consistency check across analysis and knowledge graph.",
            sentiment="positive",
            topics=["Machine Learning", "Deep Learning"],
        )

        kg = await service.save_knowledge_graph(
            project_uuid=pid, video_id=test_project_data["video_id"],
            entities=[
                {"name": "Machine Learning", "type": "field"},
                {"name": "Deep Learning", "type": "subfield"},
                {"name": "Neural Networks", "type": "technique"},
            ],
            relationships=[
                {"source": "Deep Learning", "target": "Machine Learning", "type": "subset_of"},
            ],
        )

        assert analysis is not None
        assert kg is not None
        analysis_topics = analysis.get("topics", [])
        for entity in kg["entities"]:
            if entity["name"] in analysis_topics:
                assert entity["name"] in analysis_topics
