from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestOutputStability:
    @pytest.mark.asyncio
    async def test_deterministic_output(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Deterministic Test",
        )
        pid = proj["project_id"]

        seo1 = await service.save_seo(
            project_uuid=pid, primary_keyword="deterministic",
            secondary_keywords=["a", "b"],
            seo_score=85.0,
        )

        seo2 = await service.save_seo(
            project_uuid=pid, primary_keyword="deterministic",
            secondary_keywords=["a", "b"],
            seo_score=85.0,
        )

        s1_str = json.dumps({"keyword": seo1["primary_keyword"], "score": seo1["seo_score"]}, sort_keys=True)
        s2_str = json.dumps({"keyword": seo2["primary_keyword"], "score": seo2["seo_score"]}, sort_keys=True)
        h1 = hashlib.md5(s1_str.encode()).hexdigest()
        h2 = hashlib.md5(s2_str.encode()).hexdigest()

        assert seo1["primary_keyword"] == seo2["primary_keyword"]
        assert seo1["seo_score"] == seo2["seo_score"]

    @pytest.mark.asyncio
    async def test_output_format_stability(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Format Stability",
        )
        pid = proj["project_id"]

        draft = await service.save_draft(
            project_uuid=pid, draft_number=1,
            markdown_content="# Stable Format\n\nContent with stable structure.",
            word_count=8,
        )
        assert draft is not None
        assert isinstance(draft["draft_number"], int)
        assert isinstance(draft["word_count"], int)
        assert isinstance(draft["markdown_content"], str)
        assert draft["markdown_content"].startswith("#")

    @pytest.mark.asyncio
    async def test_entity_consistency(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Entity Consistency",
        )
        pid = proj["project_id"]

        kg1 = await service.save_knowledge_graph(
            project_uuid=pid, video_id=test_project_data["video_id"],
            entities=[
                {"name": "Python", "type": "language"},
                {"name": "Django", "type": "framework"},
            ],
            relationships=[{"source": "Django", "target": "Python", "type": "uses"}],
        )

        kg2 = await service.save_knowledge_graph(
            project_uuid=pid, video_id=test_project_data["video_id"],
            entities=[
                {"name": "Python", "type": "language"},
                {"name": "Django", "type": "framework"},
            ],
            relationships=[{"source": "Django", "target": "Python", "type": "uses"}],
        )

        assert len(kg1["entities"]) == len(kg2["entities"])
        assert len(kg1["relationships"]) == len(kg2["relationships"])

    @pytest.mark.asyncio
    async def test_output_hash_consistency(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
            name="Hash Consistency",
        )
        pid = proj["project_id"]

        export1 = await service.save_export(
            project_uuid=pid, export_format="json",
            filename="data.json", checksum="abc123",
            content='{"key": "value"}',
        )
        export2 = await service.save_export(
            project_uuid=pid, export_format="json",
            filename="data.json", checksum="abc123",
            content='{"key": "value"}',
        )
        assert export1["checksum"] == export2["checksum"]
        assert export1.get("content") == export2.get("content")
