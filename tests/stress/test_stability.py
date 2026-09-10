from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.stress


class TestStability:
    @pytest.mark.asyncio
    async def test_sustained_operation_stability(self, stress_config):
        with patch("database.db_service.DatabaseService.list_projects", new_callable=AsyncMock) as m:
            m.return_value = [{"project_id": "p1"}]
            svc = DatabaseService()  # noqa: F821
            results = await asyncio.gather(
                *(svc.list_projects() for _ in range(200)),
                return_exceptions=True,
            )
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0, f"{len(errors)} errors in 200 operations"
        assert len(results) == 200

    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, stress_config):
        import tracemalloc
        tracemalloc.start()
        snapshots = []
        with patch("database.db_service.DatabaseService.list_projects", new_callable=AsyncMock) as m:
            m.return_value = [{"project_id": "p1"}]
            svc = DatabaseService()  # noqa: F821
            for _ in range(10):
                for _ in range(50):
                    await svc.list_projects()
                snapshots.append(tracemalloc.take_snapshot())
        tracemalloc.stop()
        if len(snapshots) >= 2:
            growth = sum(
                stat.size_diff
                for stat in snapshots[-1].compare_to(snapshots[0], "lineno")
            )
            growth_mb = growth / (1024 * 1024)
            assert growth_mb < stress_config["memory_leak_threshold_mb"], (
                f"Memory growth {growth_mb:.1f}MB exceeds {stress_config['memory_leak_threshold_mb']}MB"
            )

    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self, stress_config):
        with patch("database.session.DatabaseSessionManager.session_factory") as m:
            call_count = 0
            original = m.return_value

            async def limited_session():
                nonlocal call_count
                call_count += 1
                if call_count > stress_config["connection_pool_size"]:
                    raise Exception("Connection pool exhausted")
                return original

            m.side_effect = limited_session
            from database.db_service import DatabaseService
            svc = DatabaseService()
            with patch.object(svc, "list_projects", new_callable=AsyncMock) as mock_list:
                mock_list.return_value = []
                results = await asyncio.gather(
                    *(svc.list_projects() for _ in range(stress_config["connection_pool_size"] + 10)),
                    return_exceptions=True,
                )
            errors = [r for r in results if isinstance(r, Exception)]
            assert len(errors) >= 10, (
                f"Expected at least 10 errors from pool exhaustion, got {len(errors)}"
            )
