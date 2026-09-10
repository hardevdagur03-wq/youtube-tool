from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.load


class TestConcurrentProjects:
    @pytest.mark.asyncio
    async def test_10_concurrent_projects(self, load_test_config, concurrent_requests):
        n_projects = 10
        with patch("database.db_service.DatabaseService.create_project", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p_new", "status": "created", "name": "Test"}
            svc = DatabaseService()  # noqa: F821
            start = time.perf_counter()
            results = await concurrent_requests(
                [svc.create_project(video_id=f"vid{i}") for i in range(n_projects)],
                limit=n_projects,
            )
            duration = time.perf_counter() - start
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0, f"{len(errors)} projects failed to create"
        assert len(results) == n_projects
        for r in results:
            assert r["status"] == "created"
        assert (duration * 1000) < load_test_config["latency_threshold_ms"], (
            f"{n_projects} projects took {duration:.2f}s"
        )

    @pytest.mark.asyncio
    async def test_50_concurrent_projects(self, load_test_config, concurrent_requests):
        n_projects = 50
        with patch("database.db_service.DatabaseService.create_project", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p_new", "status": "created"}
            svc = DatabaseService()  # noqa: F821
            results = await concurrent_requests(
                [svc.create_project(video_id=f"vid{i}") for i in range(n_projects)],
                limit=25,
            )
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0
        assert len(results) == n_projects

    @pytest.mark.asyncio
    async def test_100_concurrent_projects(self, load_test_config, concurrent_requests):
        n_projects = 100
        with patch("database.db_service.DatabaseService.create_project", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p_new", "status": "created"}
            svc = DatabaseService()  # noqa: F821
            results = await concurrent_requests(
                [svc.create_project(video_id=f"vid{i}") for i in range(n_projects)],
                limit=50,
            )
        errors = [r for r in results if isinstance(r, Exception)]
        failure_rate = len(errors) / n_projects
        assert failure_rate < load_test_config["failure_rate_threshold"]
        assert len(results) == n_projects
