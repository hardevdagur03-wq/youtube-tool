from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.load


class TestConcurrentUsers:
    @pytest.mark.asyncio
    async def test_10_concurrent_users(self, load_test_config, concurrent_requests):
        n_users = 10
        with patch("database.db_service.DatabaseService.list_projects", new_callable=AsyncMock) as m:
            m.return_value = [{"project_id": f"p{i}"} for i in range(5)]
            from database.db_service import DatabaseService
            svc = DatabaseService()
            start = time.perf_counter()
            results = await concurrent_requests([svc.list_projects() for _ in range(n_users)], limit=n_users)
            duration = time.perf_counter() - start
        errors = [r for r in results if isinstance(r, Exception)]
        latency_ms = duration * 1000
        assert latency_ms < load_test_config["latency_threshold_ms"], (
            f"{n_users} concurrent users latency {latency_ms:.0f}ms"
        )
        assert len(errors) == 0, f"{len(errors)} errors out of {n_users}"
        assert len(results) == n_users

    @pytest.mark.asyncio
    async def test_100_concurrent_users(self, load_test_config, concurrent_requests):
        n_users = 100
        with patch("database.db_service.DatabaseService.list_projects", new_callable=AsyncMock) as m:
            m.return_value = [{"project_id": f"p{i}"} for i in range(5)]
            svc = DatabaseService()  # noqa: F821
            start = time.perf_counter()
            results = await concurrent_requests([svc.list_projects() for _ in range(n_users)], limit=50)
            duration = time.perf_counter() - start
        errors = [r for r in results if isinstance(r, Exception)]
        failure_rate = len(errors) / n_users
        assert failure_rate < load_test_config["failure_rate_threshold"], (
            f"Failure rate {failure_rate:.2%} exceeds {load_test_config['failure_rate_threshold']:.0%}"
        )
        assert duration < 5.0, f"100 users took {duration:.2f}s"

    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_500_concurrent_users(self, load_test_config, concurrent_requests):
        n_users = 500
        with patch("database.db_service.DatabaseService.list_projects", new_callable=AsyncMock) as m:
            m.return_value = [{"project_id": f"p{i}"} for i in range(5)]
            svc = DatabaseService()  # noqa: F821
            start = time.perf_counter()
            results = await concurrent_requests([svc.list_projects() for _ in range(n_users)], limit=100)
            duration = time.perf_counter() - start
        errors = [r for r in results if isinstance(r, Exception)]
        failure_rate = len(errors) / n_users
        assert failure_rate < load_test_config["failure_rate_threshold"]
        assert duration < 15.0, f"500 users took {duration:.2f}s"

    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_1000_concurrent_users(self, load_test_config, concurrent_requests):
        n_users = 1000
        with patch("database.db_service.DatabaseService.list_projects", new_callable=AsyncMock) as m:
            m.return_value = [{"project_id": f"p{i}"} for i in range(5)]
            svc = DatabaseService()  # noqa: F821
            start = time.perf_counter()
            results = await concurrent_requests([svc.list_projects() for _ in range(n_users)], limit=200)
            duration = time.perf_counter() - start
        errors = [r for r in results if isinstance(r, Exception)]
        failure_rate = len(errors) / n_users
        assert failure_rate < load_test_config["failure_rate_threshold"] * 2
        assert duration < 30.0, f"1000 users took {duration:.2f}s"
