from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from typing import Any

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from database.base import Base
from database.config import DatabaseConfig
from database.models import *
from database.repositories import *
from database.session import DatabaseSessionManager
from database.unit_of_work import UnitOfWork
from database.db_service import DatabaseService
from database.cache import DatabaseCache


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest_asyncio.fixture
async def init_test_database(db_path):
    mgr = DatabaseSessionManager._make_fresh()
    config = DatabaseConfig.for_testing(sqlite_path=db_path)
    mgr.initialize(config)
    await mgr.create_all()
    yield mgr
    await mgr.close()


@pytest_asyncio.fixture
async def db_session(init_test_database):
    session = init_test_database.session_factory()
    try:
        yield session
    finally:
        await session.close()


@pytest_asyncio.fixture
async def uow(init_test_database):
    session = init_test_database.session_factory()
    uow_obj = UnitOfWork(session=session)
    await uow_obj.__aenter__()
    try:
        yield uow_obj
    except Exception:
        await uow_obj.__aexit__(*sys.exc_info())
        raise
    else:
        await uow_obj.__aexit__(None, None, None)
    finally:
        await session.close()


@pytest_asyncio.fixture
async def service(init_test_database):
    svc = DatabaseService(session_manager=init_test_database)
    yield svc


@pytest.fixture
def mock_llm_provider():
    provider = MagicMock()
    provider.generate = AsyncMock(return_value={"text": "Mocked LLM response", "usage": {"total_tokens": 100}})
    provider.generate_structured = AsyncMock(return_value={"result": "mocked"})
    return provider


@pytest.fixture
def mock_youtube_client():
    client = MagicMock()
    client.get_video_metadata = AsyncMock(return_value={
        "video_id": "test123",
        "title": "Test Video Title",
        "channel_title": "Test Channel",
        "description": "A test video description for testing.",
        "view_count": 10000,
        "like_count": 500,
        "duration_seconds": 600,
        "tags": ["test", "python", "tutorial"],
        "category": "Education",
        "published_at": "2024-01-01T00:00:00Z",
    })
    client.get_transcript = AsyncMock(return_value={
        "plain_text": "This is a test transcript with enough content to test the full pipeline. Python is a programming language. It is used for data science and web development. Machine learning is a popular application. Artificial intelligence is transforming industries.",
        "segments": [
            {"text": "This is a test transcript.", "start": 0.0, "duration": 5.0},
            {"text": "Python is a programming language.", "start": 5.0, "duration": 4.0},
            {"text": "It is used for data science.", "start": 9.0, "duration": 3.0},
        ],
        "language": "en",
        "word_count": 50,
    })
    return client


@pytest.fixture
def test_project_data():
    return {
        "url": "https://youtube.com/watch?v=test123",
        "video_id": "test123",
        "name": "Integration Test Project",
        "language": "en",
        "settings": {
            "seo_enabled": True,
            "export_formats": ["markdown", "html", "json"],
            "target_word_count": 1500,
            "tone": "professional",
        },
    }


@pytest.fixture
def golden_dataset():
    return {
        "metadata": {
            "title": "Test Video Title",
            "channel_title": "Test Channel",
            "view_count": 10000,
        },
        "transcript": {
            "word_count": 50,
            "language": "en",
            "has_segments": True,
        },
        "analysis": {
            "primary_topic": "Python Programming",
            "sentiment": "positive",
            "key_takeaways_count": 3,
        },
        "knowledge_graph": {
            "entity_count": 5,
            "relationship_count": 3,
            "has_topics": True,
        },
        "seo": {
            "primary_keyword": "Python programming",
            "seo_score_min": 70.0,
            "has_meta": True,
        },
        "outline": {
            "section_count_min": 5,
            "has_title": True,
            "has_intro": True,
        },
        "draft": {
            "word_count_min": 500,
            "has_markdown": True,
            "section_count_min": 5,
        },
        "review": {
            "overall_score_min": 60.0,
            "has_grammar_check": True,
            "has_seo_check": True,
        },
        "optimization": {
            "score_improvement_min": 1.0,
            "has_optimized_content": True,
        },
    }


@pytest_asyncio.fixture
async def full_pipeline_context(service, test_project_data):
    project = await service.create_project(
        url=test_project_data["url"],
        video_id=test_project_data["video_id"],
        name=test_project_data["name"],
    )
    yield {"project": project, "service": service}
