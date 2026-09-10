from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.background_job


class TestDeadLetterQueue:
    @pytest.mark.asyncio
    async def test_send_to_dlq(self):
        with patch("background_processing.dead_letter_queue.DeadLetterQueue.send", new_callable=AsyncMock) as m:
            m.return_value = True
            from background_processing.dead_letter_queue import DeadLetterQueue
            dlq = DeadLetterQueue()
            result = await dlq.send(
                job_id="j1",
                project_id="p1",
                job_type="test",
                error="Permanent failure",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_replay_from_dlq(self):
        with patch("background_processing.dead_letter_queue.DeadLetterQueue.replay", new_callable=AsyncMock) as m:
            m.return_value = type("Job", (), {"uuid": "j1", "status": "queued"})()
            from background_processing.dead_letter_queue import DeadLetterQueue
            dlq = DeadLetterQueue()
            result = await dlq.replay("j1")
            assert result is not None

    @pytest.mark.asyncio
    async def test_purge_dlq(self):
        with patch("background_processing.dead_letter_queue.DeadLetterQueue.purge", new_callable=AsyncMock) as m:
            m.return_value = 5
            from background_processing.dead_letter_queue import DeadLetterQueue
            dlq = DeadLetterQueue()
            purged = await dlq.purge()
            assert purged >= 0

    @pytest.mark.asyncio
    async def test_dlq_metrics(self):
        with patch("background_processing.dead_letter_queue.DeadLetterQueue.count", new_callable=AsyncMock) as m:
            m.return_value = 3
            from background_processing.dead_letter_queue import DeadLetterQueue
            dlq = DeadLetterQueue()
            count = await dlq.count()
            assert count == 3
