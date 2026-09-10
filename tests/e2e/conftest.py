from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


@pytest.fixture
def test_client():
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token-for-testing"}


@pytest_asyncio.fixture
async def test_project_id(service, test_project_data):
    from database.db_service import DatabaseService
    proj = await service.create_project(
        url=test_project_data["url"],
        video_id=test_project_data["video_id"],
        name="E2E Test Project",
    )
    return proj["project_id"]


@pytest.fixture
def test_video_url():
    return "https://youtube.com/watch?v=dQw4w9WgXcQ"


@pytest_asyncio.fixture
async def service():
    from database.config import DatabaseConfig
    from database.session import DatabaseSessionManager
    from database.db_service import DatabaseService

    mgr = DatabaseSessionManager._make_fresh()
    config = DatabaseConfig.for_testing(sqlite_path=":memory:")
    mgr.initialize(config)
    await mgr.create_all()
    svc = DatabaseService(session_manager=mgr)
    yield svc
    await mgr.close()


@pytest.fixture
def test_project_data():
    return {
        "url": "https://youtube.com/watch?v=e2etest",
        "video_id": "e2etest",
        "name": "E2E Test Project",
        "language": "en",
    }
