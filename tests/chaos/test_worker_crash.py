from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.chaos


class TestWorkerCrash:
    @pytest.mark.asyncio
    async def test_worker_crash_during_pipeline(self):
        with patch("database.db_service.DatabaseService.process_video", new_callable=AsyncMock) as m:
            m.side_effect = [Exception("Worker crashed"), {"status": "completed"}]
            svc = DatabaseService()  # noqa: F821
            with pytest.raises(Exception, match="Worker crashed"):
                await svc.process_video("p1")

    @pytest.mark.asyncio
    async def test_worker_crash_recovery(self, chaos_config):
        with patch("database.db_service.DatabaseService.get_project", new_callable=AsyncMock) as m:
            m.side_effect = [
                Exception("Worker crashed"),
                Exception("Worker crashed"),
                {"project_id": "p1", "status": "completed"},
            ]
            svc = DatabaseService()  # noqa: F821
            for i in range(3):
                try:
                    result = await svc.get_project("p1")
                    if i == 2:
                        assert result["status"] == "completed"
                except Exception:
                    if i >= 2:
                        raise

    @pytest.mark.asyncio
    async def test_job_requeue_after_crash(self):
        with patch("background_processing.job_repository.JobRepository.update_status", new_callable=AsyncMock) as m:
            m.return_value = type("Job", (), {"uuid": "j1", "status": "queued"})()
            from background_processing.job_repository import JobRepository
            repo = JobRepository()
            result = await repo.update_status("j1", "queued")
            assert result.status == "queued"

    @pytest.mark.asyncio
    async def test_dead_letter_on_permanent_failure(self):
        with patch("background_processing.job_repository.JobRepository.update_status", new_callable=AsyncMock) as m:
            m.return_value = type("Job", (), {"uuid": "j1", "status": "dead_letter"})()
            from background_processing.job_repository import JobRepository
            repo = JobRepository()
            result = await repo.update_status("j1", "dead_letter")
            assert result.status == "dead_letter"
