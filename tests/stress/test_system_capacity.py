from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.stress


class TestSystemCapacity:
    @pytest.mark.asyncio
    async def test_maximum_concurrent_pipelines(self, stress_config):
        n_pipelines = stress_config["max_concurrent_pipelines"]
        with patch("database.db_service.DatabaseService.create_project", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p", "status": "created"}
            with patch("database.db_service.DatabaseService.process_video", new_callable=AsyncMock) as m2:
                m2.return_value = {"status": "completed"}
                svc = DatabaseService()  # noqa: F821
                start = time.perf_counter()
                results = await asyncio.gather(
                    *(
                        svc.create_project(video_id=f"vid{i}")
                        for i in range(n_pipelines)
                    ),
                    return_exceptions=True,
                )
                duration = time.perf_counter() - start
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0, f"{len(errors)} pipelines failed out of {n_pipelines}"
        assert len(results) == n_pipelines
        assert duration < 30.0, f"{n_pipelines} pipelines took {duration:.2f}s"

    @pytest.mark.asyncio
    async def test_maximum_queue_depth(self, stress_config):
        depth = stress_config["max_queue_depth"]
        with patch("background_processing.job_repository.JobRepository.create", new_callable=AsyncMock) as m:
            m.return_value = type("Job", (), {"uuid": "j", "status": "queued"})()
            from background_processing.job_repository import JobRepository
            repo = JobRepository()
            results = await asyncio.gather(
                *(repo.create(job_type="stress", payload={"n": i}) for i in range(min(depth, 500))),
                return_exceptions=True,
            )
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0, f"{len(errors)} jobs failed to enqueue"

    @pytest.mark.asyncio
    async def test_sustained_load_over_period(self, stress_config):
        duration_s = min(stress_config["sustained_load_duration_s"], 10)
        with patch("database.db_service.DatabaseService.get_project", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p1", "name": "Stress", "status": "completed"}
            svc = DatabaseService()  # noqa: F821
            start = time.perf_counter()
            count = 0
            while time.perf_counter() - start < duration_s:
                await svc.get_project("p1")
                count += 1
            elapsed = time.perf_counter() - start
        ops_per_sec = count / elapsed
        assert ops_per_sec > 100, (
            f"Sustained throughput {ops_per_sec:.0f} ops/sec below 100"
        )
        assert count > 0
