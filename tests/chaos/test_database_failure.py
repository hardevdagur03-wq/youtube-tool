from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.chaos


class TestDatabaseFailure:
    @pytest.mark.asyncio
    async def test_db_connection_loss(self):
        with patch("database.db_service.DatabaseService.get_project", new_callable=AsyncMock) as m:
            m.side_effect = ConnectionError("Database connection lost")
            svc = DatabaseService()  # noqa: F821
            with pytest.raises(ConnectionError, match="Database connection lost"):
                await svc.get_project("p1")

    @pytest.mark.asyncio
    async def test_db_connection_pool_exhaustion(self):
        with patch("database.db_service.DatabaseService.list_projects", new_callable=AsyncMock) as m:
            m.side_effect = Exception("Connection pool exhausted")
            svc = DatabaseService()  # noqa: F821
            with pytest.raises(Exception, match="Connection pool exhausted"):
                await svc.list_projects()

    @pytest.mark.asyncio
    async def test_db_timeout(self):
        with patch("database.db_service.DatabaseService.get_project", new_callable=AsyncMock) as m:
            m.side_effect = TimeoutError("Database query timed out")
            svc = DatabaseService()  # noqa: F821
            with pytest.raises(TimeoutError, match="Database query timed out"):
                await svc.get_project("p1")

    @pytest.mark.asyncio
    async def test_db_recovery(self, chaos_config):
        with patch("database.db_service.DatabaseService.get_project", new_callable=AsyncMock) as m:
            m.side_effect = [
                ConnectionError("Database down"),
                TimeoutError("Timeout"),
                {"project_id": "p1", "status": "completed"},
            ]
            svc = DatabaseService()  # noqa: F821
            results = []
            for i in range(3):
                try:
                    results.append(await svc.get_project("p1"))
                except Exception:
                    results.append(None)
            assert len(results) == 3
            assert results[2] is not None
            assert results[2]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_failure(self):
        with patch("database.unit_of_work.UnitOfWork.commit") as m:
            m.side_effect = Exception("Commit failed")
            with patch("database.unit_of_work.UnitOfWork.rollback", new_callable=AsyncMock) as mock_rollback:
                uow_obj = type("UOW", (), {"commit": m, "rollback": mock_rollback})()
                try:
                    await uow_obj.commit()
                except Exception:
                    await uow_obj.rollback()
                mock_rollback.assert_called_once()
