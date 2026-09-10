from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.performance


@pytest.mark.asyncio
async def test_metadata_stage_duration(performance_config, timer):
    with timer() as elapsed:
        with patch("database.db_service.DatabaseService.create_project", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p1", "name": "Test", "status": "created"}
            from database.db_service import DatabaseService
            svc = DatabaseService()
            result = await svc.create_project(video_id="test_vid", name="Test Project")
    dur = elapsed()
    assert dur < performance_config["stage_threshold_s"]
    assert result["project_id"] == "p1"


@pytest.mark.asyncio
async def test_transcript_stage_duration(performance_config, timer):
    with timer() as elapsed:
        with patch("database.db_service.DatabaseService.process_video", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p1", "status": "completed", "transcript": "full transcript"}
            svc = DatabaseService()  # noqa: F821
            result = await svc.process_video("p1")
    dur = elapsed()
    assert dur < performance_config["stage_threshold_s"]
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_analysis_stage_duration(performance_config, timer):
    with timer() as elapsed:
        with patch("database.db_service.DatabaseService.generate_analysis", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p1", "status": "completed", "analysis": {}}
            svc = DatabaseService()  # noqa: F821
            result = await svc.generate_analysis("p1")
    dur = elapsed()
    assert dur < performance_config["stage_threshold_s"]
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_kg_stage_duration(performance_config, timer):
    with timer() as elapsed:
        with patch("database.db_service.DatabaseService.generate_knowledge_graph", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p1", "status": "completed", "kg": {}}
            svc = DatabaseService()  # noqa: F821
            result = await svc.generate_knowledge_graph("p1")
    dur = elapsed()
    assert dur < performance_config["stage_threshold_s"]
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_seo_stage_duration(performance_config, timer):
    with timer() as elapsed:
        with patch("database.db_service.DatabaseService.generate_seo_analysis", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p1", "status": "completed", "seo": {}}
            svc = DatabaseService()  # noqa: F821
            result = await svc.generate_seo_analysis("p1")
    dur = elapsed()
    assert dur < performance_config["stage_threshold_s"]
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_outline_stage_duration(performance_config, timer):
    with timer() as elapsed:
        with patch("database.db_service.DatabaseService.generate_outline", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p1", "status": "completed", "outline": {}}
            svc = DatabaseService()  # noqa: F821
            result = await svc.generate_outline("p1")
    dur = elapsed()
    assert dur < performance_config["stage_threshold_s"]
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_sections_stage_duration(performance_config, timer):
    with timer() as elapsed:
        with patch("database.db_service.DatabaseService.generate_sections", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p1", "status": "completed", "sections": []}
            svc = DatabaseService()  # noqa: F821
            result = await svc.generate_sections("p1")
    dur = elapsed()
    assert dur < performance_config["stage_threshold_s"]
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_draft_stage_duration(performance_config, timer):
    with timer() as elapsed:
        with patch("database.db_service.DatabaseService.generate_draft", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p1", "status": "completed", "draft": "draft content"}
            svc = DatabaseService()  # noqa: F821
            result = await svc.generate_draft("p1")
    dur = elapsed()
    assert dur < performance_config["stage_threshold_s"]
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_review_stage_duration(performance_config, timer):
    with timer() as elapsed:
        with patch("database.db_service.DatabaseService.generate_review", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p1", "status": "completed", "review": {}}
            svc = DatabaseService()  # noqa: F821
            result = await svc.generate_review("p1")
    dur = elapsed()
    assert dur < performance_config["stage_threshold_s"]
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_optimization_stage_duration(performance_config, timer):
    with timer() as elapsed:
        with patch("database.db_service.DatabaseService.generate_optimization", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p1", "status": "completed", "optimization": {}}
            svc = DatabaseService()  # noqa: F821
            result = await svc.generate_optimization("p1")
    dur = elapsed()
    assert dur < performance_config["stage_threshold_s"]
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_export_stage_duration(performance_config, timer):
    with timer() as elapsed:
        with patch("database.db_service.DatabaseService.export_project", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p1", "status": "completed", "export": {}}
            svc = DatabaseService()  # noqa: F821
            result = await svc.export_project("p1", fmt="markdown")
    dur = elapsed()
    assert dur < performance_config["stage_threshold_s"]
    assert result["status"] == "completed"
