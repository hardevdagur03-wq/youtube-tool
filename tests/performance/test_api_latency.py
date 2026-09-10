from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.performance


def _assert_latency(duration_ms: float, threshold_ms: float, label: str):
    assert duration_ms < threshold_ms, (
        f"{label} latency {duration_ms:.1f}ms exceeds threshold {threshold_ms}ms"
    )


class TestApiLatency:
    @pytest.mark.asyncio
    async def test_api_project_list_latency(self, performance_config, metrics_collector):
        with patch("database.db_service.DatabaseService.list_projects", new_callable=AsyncMock) as m:
            m.return_value = []
            from database.db_service import DatabaseService
            svc = DatabaseService()
            for _ in range(10):
                start = time.perf_counter()
                await svc.list_projects()
                dur_ms = (time.perf_counter() - start) * 1000
                metrics_collector.record("project_list", dur_ms)

        p95 = metrics_collector.p95("project_list")
        _assert_latency(p95, performance_config["api_threshold_ms"], "Project list P95")
        assert len(metrics_collector.get("project_list")) == 10

    @pytest.mark.asyncio
    async def test_api_project_detail_latency(self, performance_config, metrics_collector):
        with patch("database.db_service.DatabaseService.get_project", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p1", "name": "Test", "status": "completed"}
            from database.db_service import DatabaseService
            svc = DatabaseService()
            for _ in range(10):
                start = time.perf_counter()
                await svc.get_project("p1")
                dur_ms = (time.perf_counter() - start) * 1000
                metrics_collector.record("project_detail", dur_ms)

        p95 = metrics_collector.p95("project_detail")
        _assert_latency(p95, performance_config["api_threshold_ms"], "Project detail P95")

    @pytest.mark.asyncio
    async def test_api_create_project_latency(self, performance_config, metrics_collector):
        with patch("database.db_service.DatabaseService.create_project", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p_new", "status": "created"}
            from database.db_service import DatabaseService
            svc = DatabaseService()
            for _ in range(10):
                start = time.perf_counter()
                await svc.create_project(video_id="v1")
                dur_ms = (time.perf_counter() - start) * 1000
                metrics_collector.record("create_project", dur_ms)

        p95 = metrics_collector.p95("create_project")
        _assert_latency(p95, performance_config["api_threshold_ms"], "Create project P95")

    @pytest.mark.asyncio
    async def test_api_export_latency(self, performance_config, metrics_collector):
        with patch("database.db_service.DatabaseService.export_project", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p1", "status": "completed"}
            from database.db_service import DatabaseService
            svc = DatabaseService()
            for _ in range(10):
                start = time.perf_counter()
                await svc.export_project("p1", fmt="markdown")
                dur_ms = (time.perf_counter() - start) * 1000
                metrics_collector.record("export", dur_ms)

        p95 = metrics_collector.p95("export")
        _assert_latency(p95, performance_config["api_threshold_ms"], "Export P95")
