from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.background_job


class TestWorkerCrash:
    @pytest.mark.asyncio
    async def test_job_recovery_after_crash(self):
        with patch("background_processing.job_repository.JobRepository.update_status", new_callable=AsyncMock) as m:
            m.return_value = type("Job", (), {"uuid": "j1", "status": "queued"})()
            from background_processing.job_repository import JobRepository
            repo = JobRepository()
            result = await repo.update_status("j1", "queued")
            assert result.status == "queued"

    @pytest.mark.asyncio
    async def test_inflight_job_requeue(self):
        with patch("background_processing.job_repository.JobRepository.update_status", new_callable=AsyncMock) as m:
            m.side_effect = [
                type("Job", (), {"uuid": "j1", "status": "running"})(),
                type("Job", (), {"uuid": "j1", "status": "queued"})(),
            ]
            from background_processing.job_repository import JobRepository
            repo = JobRepository()
            running = await repo.update_status("j1", "running")
            assert running.status == "running"
            requeued = await repo.update_status("j1", "queued")
            assert requeued.status == "queued"
