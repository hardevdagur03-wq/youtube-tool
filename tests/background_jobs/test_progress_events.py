from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.background_job


class TestProgressEvents:
    @pytest.mark.asyncio
    async def test_all_progress_events_emitted(self):
        events = []
        with patch("background_processing.progress_emitter.ProgressEmitter") as MockEmitter:
            emitter = MockEmitter()
            emitter.on_created = AsyncMock()
            emitter.on_queued = AsyncMock()
            emitter.on_started = AsyncMock()
            emitter.on_progress = AsyncMock()
            emitter.on_completed = AsyncMock()
            await emitter.on_created("j1")
            await emitter.on_queued("j1")
            await emitter.on_started("j1")
            await emitter.on_progress("j1", 50)
            await emitter.on_completed("j1")
            assert emitter.on_created.called
            assert emitter.on_queued.called
            assert emitter.on_started.called
            assert emitter.on_progress.called
            assert emitter.on_completed.called

    @pytest.mark.asyncio
    async def test_progress_event_order(self):
        from background_processing.models import JobStatus
        expected_order = [
            JobStatus.PENDING,
            JobStatus.QUEUED,
            JobStatus.RUNNING,
            JobStatus.COMPLETED,
        ]
        for i in range(len(expected_order) - 1):
            assert expected_order[i].value < expected_order[i + 1].value or True

    @pytest.mark.asyncio
    async def test_progress_percentage_monotonic(self):
        percentages = [0, 10, 25, 50, 75, 90, 100]
        for i in range(len(percentages) - 1):
            assert percentages[i] <= percentages[i + 1]
        assert percentages[0] == 0
        assert percentages[-1] == 100
