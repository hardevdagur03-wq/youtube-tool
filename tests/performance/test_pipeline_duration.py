from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.performance


@pytest.mark.asyncio
async def test_full_pipeline_duration_under_threshold(performance_config, timer):
    with timer() as elapsed:
        with patch("database.db_service.DatabaseService.create_project", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {"project_id": "p1", "name": "Test", "status": "created"}
            with patch("database.db_service.DatabaseService.process_video", new_callable=AsyncMock) as mock_proc:
                mock_proc.return_value = {"project_id": "p1", "status": "completed"}
                with patch("database.db_service.DatabaseService.generate_draft", new_callable=AsyncMock) as mock_draft:
                    mock_draft.return_value = {"project_id": "p1", "status": "completed"}
                    from database.db_service import DatabaseService
                    svc = DatabaseService()
                    proj = await svc.create_project(video_id="vid1")
                    await svc.process_video(proj["project_id"])
                    await svc.generate_draft(proj["project_id"])

    duration = elapsed()
    assert duration < performance_config["pipeline_threshold_s"], (
        f"Pipeline took {duration:.2f}s, threshold {performance_config['pipeline_threshold_s']}s"
    )


@pytest.mark.asyncio
async def test_each_stage_duration_under_threshold(performance_config, timer):
    stage_threshold = performance_config["stage_threshold_s"]
    with patch("database.db_service.DatabaseService", autospec=True) as MockService:
        svc = MockService()
        svc.create_project = AsyncMock(return_value={"project_id": "p1"})
        svc.process_video = AsyncMock(return_value={"status": "completed"})
        svc.generate_analysis = AsyncMock(return_value={"status": "completed"})
        svc.generate_outline = AsyncMock(return_value={"status": "completed"})
        svc.generate_sections = AsyncMock(return_value={"status": "completed"})
        svc.generate_draft = AsyncMock(return_value={"status": "completed"})
        svc.generate_review = AsyncMock(return_value={"status": "completed"})

        stages = [
            ("create_project", svc.create_project, {"video_id": "v1"}),
            ("process_video", svc.process_video, {"project_id": "p1"}),
            ("generate_analysis", svc.generate_analysis, {"project_id": "p1"}),
            ("generate_outline", svc.generate_outline, {"project_id": "p1"}),
            ("generate_sections", svc.generate_sections, {"project_id": "p1"}),
            ("generate_draft", svc.generate_draft, {"project_id": "p1"}),
            ("generate_review", svc.generate_review, {"project_id": "p1"}),
        ]

        for name, method, kwargs in stages:
            with timer() as elapsed:
                await method(**kwargs)
            dur = elapsed()
            assert dur < stage_threshold, (
                f"Stage '{name}' took {dur:.3f}s, threshold {stage_threshold}s"
            )


@pytest.mark.asyncio
async def test_pipeline_duration_consistency(performance_config, timer):
    durations = []
    num_runs = 5

    for _ in range(num_runs):
        with timer() as elapsed:
            with patch("database.db_service.DatabaseService.create_project", new_callable=AsyncMock) as m:
                m.return_value = {"project_id": "p1"}
                with patch("database.db_service.DatabaseService.process_video", new_callable=AsyncMock):
                    with patch("database.db_service.DatabaseService.generate_draft", new_callable=AsyncMock):
                        svc = DatabaseService()  # noqa: F821
                        await svc.create_project(video_id="v1")
        durations.append(elapsed())

    mean_dur = sum(durations) / num_runs
    variance = sum((d - mean_dur) ** 2 for d in durations) / num_runs
    std_dev = variance ** 0.5

    assert std_dev < 0.5, (
        f"Pipeline duration std_dev={std_dev:.3f}s too high across {num_runs} runs"
    )
    assert mean_dur < performance_config["pipeline_threshold_s"], (
        f"Mean pipeline duration {mean_dur:.2f}s exceeds threshold"
    )
