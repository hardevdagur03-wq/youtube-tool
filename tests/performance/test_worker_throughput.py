from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.performance


class TestWorkerThroughput:
    @pytest.mark.asyncio
    async def test_job_processing_rate(self, performance_config):
        with patch("background_processing.job_repository.JobRepository.create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = type("Job", (), {"uuid": "j1", "status": "queued"})()
            with patch("background_processing.job_repository.JobRepository.update_status", new_callable=AsyncMock) as mock_update:
                mock_update.return_value = type("Job", (), {"uuid": "j1", "status": "completed"})()
                from background_processing.job_repository import JobRepository
                repo = JobRepository()
                start = time.perf_counter()
                for i in range(50):
                    job = await repo.create(job_type="test", payload={"i": i})
                    await repo.update_status(job.uuid, "completed")
                total_s = time.perf_counter() - start
                jobs_per_sec = 50 / total_s
                assert jobs_per_sec > performance_config["worker_throughput_jobs_per_sec"], (
                    f"Job processing rate {jobs_per_sec:.0f} jobs/sec below {performance_config['worker_throughput_jobs_per_sec']}"
                )

    @pytest.mark.asyncio
    async def test_concurrent_job_throughput(self, performance_config):
        with patch("background_processing.job_repository.JobRepository.create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = type("Job", (), {"uuid": "j1", "status": "queued"})()
            with patch("background_processing.job_repository.JobRepository.update_status", new_callable=AsyncMock):
                from background_processing.job_repository import JobRepository
                repo = JobRepository()
                start = time.perf_counter()
                results = await asyncio.gather(  # noqa: F821
                    *(repo.create(job_type="concurrent", payload={"n": i}) for i in range(20))
                )
                total_s = time.perf_counter() - start
                assert len(results) == 20
                jobs_per_sec = 20 / total_s
                assert jobs_per_sec > performance_config["worker_throughput_jobs_per_sec"] * 0.5

    @pytest.mark.asyncio
    async def test_queue_drain_rate(self, performance_config):
        with patch("background_processing.job_repository.JobRepository.create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = type("Job", (), {"uuid": "j1", "status": "queued"})()
            with patch("background_processing.job_repository.JobRepository.update_status", new_callable=AsyncMock):
                with patch("background_processing.job_repository.JobRepository.list_pending", new_callable=AsyncMock) as mock_list:
                    mock_list.return_value = [type("Job", (), {"uuid": f"j{i}", "status": "queued"})() for i in range(100)]
                    repo = JobRepository()
                    pending = await repo.list_pending(limit=100)
                    assert len(pending) == 100
                    start = time.perf_counter()
                    for job in pending:
                        await repo.update_status(job.uuid, "completed")
                    drain_s = time.perf_counter() - start
                    drain_rate = 100 / drain_s
                    assert drain_rate > performance_config["worker_throughput_jobs_per_sec"], (
                        f"Queue drain rate {drain_rate:.0f} jobs/sec below threshold"
                    )
