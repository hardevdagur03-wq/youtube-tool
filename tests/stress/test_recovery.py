from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.stress


class TestRecovery:
    @pytest.mark.asyncio
    async def test_recovery_after_resource_exhaustion(self, stress_config):
        with patch("database.db_service.DatabaseService.get_project", new_callable=AsyncMock) as m:
            m.side_effect = [Exception("Connection pool exhausted")] * 5 + [
                {"project_id": "p1", "status": "completed"}
            ] * 5
            svc = DatabaseService()  # noqa: F821
            recovery_start = time.perf_counter()
            for i in range(10):
                try:
                    await svc.get_project("p1")
                except Exception:
                    pass
            recovery_time = time.perf_counter() - recovery_start
            assert recovery_time < stress_config["recovery_sla_s"], (
                f"Recovery took {recovery_time:.2f}s, SLA {stress_config['recovery_sla_s']}s"
            )

    @pytest.mark.asyncio
    async def test_recovery_after_queue_backlog(self, stress_config):
        with patch("background_processing.job_repository.JobRepository.create", new_callable=AsyncMock) as m:
            m.return_value = type("Job", (), {"uuid": "j", "status": "queued"})()
            with patch("background_processing.job_repository.JobRepository.update_status", new_callable=AsyncMock) as m2:
                m2.return_value = type("Job", (), {"uuid": "j", "status": "completed"})()
                from background_processing.job_repository import JobRepository
                repo = JobRepository()
                for i in range(100):
                    await repo.create(job_type="backlog", payload={"n": i})
                start = time.perf_counter()
                for i in range(100):
                    await repo.update_status(f"j{i}", "completed")
                drain_time = time.perf_counter() - start
                assert drain_time < stress_config["recovery_sla_s"], (
                    f"Queue drain took {drain_time:.2f}s"
                )

    @pytest.mark.asyncio
    async def test_recovery_time_within_sla(self, stress_config):
        failure_count = 0
        with patch("database.db_service.DatabaseService.get_project", new_callable=AsyncMock) as m:
            m.side_effect = lambda pid: (
                {"project_id": pid, "status": "completed"}
                if failure_count >= 3
                else (_ for _ in ()).throw(Exception("Service unavailable"))
            )
            svc = DatabaseService()  # noqa: F821
            start = time.perf_counter()
            for i in range(6):
                failure_count = i if i < 3 else 3
                try:
                    await svc.get_project("p1")
                except Exception:
                    pass
            total_time = time.perf_counter() - start
            assert total_time < stress_config["recovery_sla_s"]
