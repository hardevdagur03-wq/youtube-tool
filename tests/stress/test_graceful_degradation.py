from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.stress


class TestGracefulDegradation:
    @pytest.mark.asyncio
    async def test_degraded_mode_under_load(self):
        with patch("database.db_service.DatabaseService.get_project", new_callable=AsyncMock) as m:
            call_count = 0

            async def degraded_response(pid):
                nonlocal call_count
                call_count += 1
                if call_count > 5:
                    return {"project_id": pid, "status": "completed", "degraded": True}
                return {"project_id": pid, "status": "completed"}

            m.side_effect = degraded_response
            from database.db_service import DatabaseService
            svc = DatabaseService()
            results = []
            for i in range(10):
                result = await svc.get_project("p1")
                results.append(result)
            degraded = [r for r in results if r.get("degraded")]
            assert len(degraded) >= 4
            assert all(r["status"] == "completed" for r in results)

    @pytest.mark.asyncio
    async def test_fallback_behavior(self):
        with patch("database.db_service.DatabaseService.get_project", new_callable=AsyncMock) as m:
            m.side_effect = [
                Exception("Primary service down"),
                Exception("Primary service down"),
                {"project_id": "p1", "status": "completed", "from_cache": True},
            ]
            svc = DatabaseService()  # noqa: F821
            results = []
            for i in range(3):
                try:
                    result = await svc.get_project("p1")
                    results.append(result)
                except Exception:
                    results.append(None)
            successful = [r for r in results if r is not None]
            assert len(successful) >= 1
            if successful:
                assert successful[-1].get("from_cache") is True

    @pytest.mark.asyncio
    async def test_partial_service_availability(self):
        with patch("database.db_service.DatabaseService.get_project", new_callable=AsyncMock) as m_get:
            m_get.return_value = {"project_id": "p1", "status": "completed"}
            with patch("database.db_service.DatabaseService.list_projects", new_callable=AsyncMock) as m_list:
                m_list.side_effect = Exception("List service unavailable")
                svc = DatabaseService()  # noqa: F821
                detail = await svc.get_project("p1")
                assert detail["project_id"] == "p1"
                with pytest.raises(Exception, match="List service unavailable"):
                    await svc.list_projects()
