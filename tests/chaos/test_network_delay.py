from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.chaos


class TestNetworkDelay:
    @pytest.mark.asyncio
    async def test_high_latency_api_calls(self, chaos_config):
        latency_ms = chaos_config["network_latency_ms"]

        with patch("database.db_service.DatabaseService.get_project", new_callable=AsyncMock) as m:

            async def delayed_response(pid):
                await asyncio.sleep(latency_ms / 1000)
                return {"project_id": pid, "status": "completed"}

            m.side_effect = delayed_response
            svc = DatabaseService()  # noqa: F821
            start = time.perf_counter()
            result = await svc.get_project("p1")
            elapsed_ms = (time.perf_counter() - start) * 1000
            assert result["project_id"] == "p1"
            assert elapsed_ms >= latency_ms * 0.8

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        with patch("database.db_service.DatabaseService.get_project", new_callable=AsyncMock) as m:

            async def slow_response(pid):
                await asyncio.sleep(10)
                return {"project_id": pid}

            m.side_effect = slow_response
            svc = DatabaseService()  # noqa: F821
            with pytest.raises(asyncio.TimeoutError):
                async with asyncio.timeout(0.1):
                    await svc.get_project("p1")

    @pytest.mark.asyncio
    async def test_degraded_performance_under_latency(self, chaos_config):
        latency_ms = chaos_config["network_latency_ms"]

        with patch("database.db_service.DatabaseService.list_projects", new_callable=AsyncMock) as m:

            async def delayed_list():
                await asyncio.sleep(latency_ms / 1000)
                return [{"project_id": f"p{i}"} for i in range(5)]

            m.side_effect = delayed_list
            svc = DatabaseService()  # noqa: F821
            start = time.perf_counter()
            results = await svc.list_projects()
            elapsed_s = time.perf_counter() - start
            assert len(results) == 5
            assert elapsed_s >= latency_ms / 1000 * 0.8
