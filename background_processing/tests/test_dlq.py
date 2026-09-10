"""Tests for DeadLetterQueue — Redis-backed DLQ with replay/purge."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from background_processing.dead_letter_queue import DeadLetterQueue, RECOVERY_RULES
from background_processing.models import JobModel, DeadLetterEntry


def _make_job(job_id: str = "job-001", job_type: str = "pipeline.test",
              project_id: str = "proj-1") -> JobModel:
    return JobModel(
        uuid=job_id,
        job_type=job_type,
        project_id=project_id,
        status="failed",
        queue="default",
        payload={"key": "value"},
        retry_history=[],
    )


class TestDeadLetterQueue:
    async def test_send_to_dlq(self, mock_redis):
        dlq = DeadLetterQueue(redis_client=mock_redis)
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.lpush = AsyncMock(return_value=1)
        mock_redis.ltrim = AsyncMock(return_value=True)

        job = _make_job()
        entry = await dlq.send(job, error="Test error")
        assert entry is not None
        assert entry.job_id == "job-001"
        assert entry.error == "Test error"
        assert entry.recovery_recommendation != ""

    async def test_send_to_dlq_with_traceback(self, mock_redis):
        dlq = DeadLetterQueue(redis_client=mock_redis)
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.lpush = AsyncMock(return_value=1)
        mock_redis.ltrim = AsyncMock(return_value=True)

        job = _make_job()
        entry = await dlq.send(job, error="TimeoutError", traceback="Traceback (most recent call last):...")
        assert "TimeoutError" in entry.error
        assert "most recent call last" in entry.traceback

    async def test_get_dlq_entry(self, mock_redis):
        dlq = DeadLetterQueue(redis_client=mock_redis)
        mock_redis.get = AsyncMock(return_value=(
            '{"job_id": "job-001", "project_id": "proj-1", "job_type": "pipeline.test", '
            '"payload": {}, "error": "err", "traceback": "", "retry_history": [], '
            '"failed_at": "2025-01-01T00:00:00", "recovery_recommendation": "Check logs", "recovered": false}'
        ))
        entry = await dlq.get("job-001")
        assert entry is not None
        assert entry.job_id == "job-001"

    async def test_get_dlq_entry_not_found(self, mock_redis):
        dlq = DeadLetterQueue(redis_client=mock_redis)
        mock_redis.get = AsyncMock(return_value=None)
        entry = await dlq.get("nonexistent")
        assert entry is None

    async def test_list_dlq(self, mock_redis):
        dlq = DeadLetterQueue(redis_client=mock_redis)
        mock_redis.lrange = AsyncMock(return_value=["job-001", "job-002"])
        mock_redis.get = AsyncMock(side_effect=[
            '{"job_id": "job-001", "project_id": "p1", "job_type": "t", "payload": {}, '
            '"error": "e1", "traceback": "", "retry_history": [], '
            '"failed_at": "2025-01-01T00:00:00", "recovery_recommendation": "R1", "recovered": false}',
            '{"job_id": "job-002", "project_id": "p1", "job_type": "t", "payload": {}, '
            '"error": "e2", "traceback": "", "retry_history": [], '
            '"failed_at": "2025-01-01T00:00:00", "recovery_recommendation": "R2", "recovered": false}',
        ])
        entries = await dlq.list(limit=10)
        assert len(entries) == 2
        assert entries[0].job_id == "job-001"
        assert entries[1].job_id == "job-002"

    async def test_list_empty_dlq(self, mock_redis):
        dlq = DeadLetterQueue(redis_client=mock_redis)
        mock_redis.lrange = AsyncMock(return_value=[])
        entries = await dlq.list()
        assert entries == []

    async def test_count_dlq(self, mock_redis):
        dlq = DeadLetterQueue(redis_client=mock_redis)
        mock_redis.llen = AsyncMock(return_value=5)
        count = await dlq.count()
        assert count == 5

    async def test_replay_job(self, mock_redis):
        dlq = DeadLetterQueue(redis_client=mock_redis)
        mock_redis.get = AsyncMock(return_value=(
            '{"job_id": "job-001", "project_id": "p1", "job_type": "t", "payload": {}, '
            '"error": "err", "traceback": "", "retry_history": [], '
            '"failed_at": "2025-01-01T00:00:00", "recovery_recommendation": "R", "recovered": false}'
        ))
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.lrem = AsyncMock(return_value=1)

        job_repo_mock = AsyncMock()
        updated_job = _make_job(job_id="job-001")
        updated_job.status = "pending"
        job_repo_mock.get = AsyncMock(return_value=_make_job(job_id="job-001"))
        job_repo_mock.update = AsyncMock(return_value=updated_job)

        result = await dlq.replay("job-001", job_repo_mock)
        assert result is not None
        assert result.status == "pending"

    async def test_replay_job_not_found_in_dlq(self, mock_redis):
        dlq = DeadLetterQueue(redis_client=mock_redis)
        mock_redis.get = AsyncMock(return_value=None)
        result = await dlq.replay("nonexistent", AsyncMock())
        assert result is None

    async def test_replay_all(self, mock_redis):
        dlq = DeadLetterQueue(redis_client=mock_redis)
        mock_redis.lrange = AsyncMock(return_value=["job-001", "job-002"])
        mock_redis.get = AsyncMock(return_value=(
            '{"job_id": "job-001", "project_id": "p1", "job_type": "t", "payload": {}, '
            '"error": "err", "traceback": "", "retry_history": [], '
            '"failed_at": "2025-01-01T00:00:00", "recovery_recommendation": "R", "recovered": false}'
        ))
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.lrem = AsyncMock(return_value=1)

        job_repo_mock = AsyncMock()
        job_repo_mock.get = AsyncMock(return_value=_make_job())
        job_repo_mock.update = AsyncMock(return_value=_make_job())

        count = await dlq.replay_all(job_repo_mock)
        assert count == 2

    async def test_purge(self, mock_redis):
        dlq = DeadLetterQueue(redis_client=mock_redis)
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.lrem = AsyncMock(return_value=1)
        result = await dlq.purge("job-001")
        assert result is True

    async def test_purge_all(self, mock_redis):
        dlq = DeadLetterQueue(redis_client=mock_redis)
        mock_redis.llen = AsyncMock(return_value=3)
        mock_redis.keys = AsyncMock(return_value=["dlq:job-001", "dlq:job-002", "dlq:job-003"])
        mock_redis.delete = AsyncMock(return_value=3)
        count = await dlq.purge_all()
        assert count == 3

    def test_recommend_recovery(self, mock_redis):
        dlq = DeadLetterQueue(redis_client=mock_redis)
        for error_type, recommendation in RECOVERY_RULES.items():
            result = dlq._recommend_recovery(error_type)
            assert result == recommendation

    def test_recommend_recovery_unknown(self, mock_redis):
        dlq = DeadLetterQueue(redis_client=mock_redis)
        result = dlq._recommend_recovery("UnknownError: something strange")
        assert result == "Check worker logs and infrastructure health."
