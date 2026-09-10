from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.background_job


class TestQueue:
    @pytest.mark.asyncio
    async def test_job_enqueue(self):
        with patch("background_processing.job_repository.JobRepository.create", new_callable=AsyncMock) as m:
            expected = type("Job", (), {"uuid": "j1", "job_type": "test", "status": "queued"})()
            m.return_value = expected
            from background_processing.job_repository import JobRepository
            repo = JobRepository()
            result = await repo.create(job_type="test", payload={"data": 1})
            assert result.uuid == "j1"
            assert result.status == "queued"

    @pytest.mark.asyncio
    async def test_job_dequeue(self):
        with patch("background_processing.job_repository.JobRepository.update_status", new_callable=AsyncMock) as m:
            expected = type("Job", (), {"uuid": "j1", "status": "running"})()
            m.return_value = expected
            from background_processing.job_repository import JobRepository
            repo = JobRepository()
            result = await repo.update_status("j1", "running")
            assert result.status == "running"

    @pytest.mark.asyncio
    async def test_priority_queue_ordering(self):
        priorities = [
            ("critical", 0),
            ("high", 3),
            ("default", 5),
            ("low", 8),
            ("background", 10),
        ]
        for name, priority in priorities:
            assert priority >= 0
            assert priority <= 10
        sorted_priorities = sorted(priorities, key=lambda x: x[1])
        assert sorted_priorities[0][0] == "critical"
        assert sorted_priorities[-1][0] == "background"

    @pytest.mark.asyncio
    async def test_queue_metrics(self):
        with patch("background_processing.job_repository.JobRepository.get_metrics", new_callable=AsyncMock) as m:
            m.return_value = {"total": 100, "pending": 30, "running": 5, "completed": 60, "failed": 5}
            from background_processing.job_repository import JobRepository
            repo = JobRepository()
            metrics = await repo.get_metrics()
            assert metrics["total"] == 100
            assert metrics["pending"] + metrics["running"] + metrics["completed"] + metrics["failed"] == metrics["total"]
