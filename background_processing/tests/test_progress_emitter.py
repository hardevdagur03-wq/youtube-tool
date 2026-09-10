"""Tests for ProgressEmitter — job lifecycle methods with DB persistence + event publishing."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from background_processing.event_bus import EventBus
from background_processing.progress_emitter import ProgressEmitter


class TestProgressEmitter:
    @pytest.fixture
    def repo(self):
        return AsyncMock()

    @pytest.fixture
    def event_bus(self):
        bus = AsyncMock(spec=EventBus)
        bus.publish_event = AsyncMock(return_value=1)
        bus.publish_progress = AsyncMock(return_value=1)
        bus.publish = AsyncMock(return_value=1)
        return bus

    @pytest.fixture
    def emitter(self, repo, event_bus):
        return ProgressEmitter(job_repo=repo, event_bus=event_bus)

    async def test_on_created(self, emitter, event_bus):
        await emitter.on_created("job-1", "proj-1", "pipeline.test")
        event_bus.publish_event.assert_awaited_once()

    async def test_on_queued(self, emitter, event_bus):
        await emitter.on_queued("job-1", "proj-1")
        event_bus.publish_event.assert_awaited_once()

    async def test_on_started(self, emitter, repo, event_bus):
        repo.update_status = AsyncMock(return_value=AsyncMock())
        await emitter.on_started("job-1", "proj-1", worker_id="w1")
        repo.update_status.assert_awaited_once_with("job-1", "running", worker_id="w1")
        event_bus.publish_event.assert_awaited_once()

    async def test_on_progress(self, emitter, repo, event_bus):
        repo.update_progress = AsyncMock(return_value=AsyncMock())
        await emitter.on_progress("job-1", "proj-1", 75.0, "Processing...", stage="analysis", detail={"step": 3})
        repo.update_progress.assert_awaited_once_with("job-1", 75.0, "Processing...", "analysis", {"step": 3})
        event_bus.publish_progress.assert_awaited_once()

    async def test_on_stage_completed(self, emitter, event_bus):
        await emitter.on_stage_completed("job-1", "proj-1", "analysis", {"result": "ok"})
        event_bus.publish_event.assert_awaited_once()

    async def test_on_stage_failed(self, emitter, event_bus):
        await emitter.on_stage_failed("job-1", "proj-1", "analysis", "error message")
        event_bus.publish_event.assert_awaited_once()

    async def test_on_completed(self, emitter, repo, event_bus):
        repo.update_status = AsyncMock(return_value=AsyncMock())
        await emitter.on_completed("job-1", "proj-1", duration_ms=2500, result={"output": "done"})
        repo.update_status.assert_awaited_once()
        call_kwargs = repo.update_status.call_args[1]
        assert call_kwargs["duration_ms"] == 2500
        assert call_kwargs["result_data"] == {"output": "done"}
        event_bus.publish_event.assert_awaited_once()

    async def test_on_failed(self, emitter, repo, event_bus):
        repo.update_status = AsyncMock(return_value=AsyncMock())
        await emitter.on_failed("job-1", "proj-1", error="fail", traceback="tb", recoverable=True)
        repo.update_status.assert_awaited_once_with(
            "job-1", "failed", error="fail", traceback="tb", recoverable=True
        )
        event_bus.publish_event.assert_awaited_once()

    async def test_on_cancelled(self, emitter, repo, event_bus):
        repo.update_status = AsyncMock(return_value=AsyncMock())
        await emitter.on_cancelled("job-1", "proj-1", reason="user request")
        repo.update_status.assert_awaited_once_with("job-1", "cancelled", error="user request")
        event_bus.publish_event.assert_awaited_once()

    async def test_on_retrying(self, emitter, repo, event_bus):
        repo.update_status = AsyncMock(return_value=AsyncMock())
        await emitter.on_retrying("job-1", "proj-1", attempt=2, max_retries=3, error="timeout")
        repo.update_status.assert_awaited_once_with("job-1", "retrying")
        event_bus.publish_event.assert_awaited_once()

    async def test_on_dead_letter(self, emitter, repo, event_bus):
        repo.update_status = AsyncMock(return_value=AsyncMock())
        await emitter.on_dead_letter("job-1", "proj-1", error="perm failure")
        repo.update_status.assert_awaited_once_with("job-1", "dead_letter", error="perm failure")
        event_bus.publish_event.assert_awaited_once()

    async def test_on_recovered(self, emitter, repo, event_bus):
        repo.update_status = AsyncMock(return_value=AsyncMock())
        await emitter.on_recovered("job-1", "proj-1")
        repo.update_status.assert_awaited_once_with("job-1", "recovered")
        event_bus.publish_event.assert_awaited_once()
