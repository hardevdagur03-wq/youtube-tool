"""Tests for the Resource Manager — concurrency and queue depth limits."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from background_processing.models import JobCreate
from background_processing.resource_manager import ResourceManager


class TestResourceManager:
    @pytest_asyncio.fixture
    async def mgr(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=0)
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.decr = AsyncMock(return_value=0)
        r = ResourceManager(redis_client=mock_redis)
        yield r

    async def test_can_accept_within_limits(self, mgr, mock_redis):
        job = JobCreate(job_type="pipeline.analysis", project_id="p1")
        result = await mgr.can_accept(job, tenant_id="tenant-1")
        assert result is True

    async def test_cannot_accept_queue_full(self, mgr, mock_redis):
        mock_redis.get.return_value = 10000
        job = JobCreate(job_type="pipeline.analysis", project_id="p1", queue="default")
        result = await mgr.can_accept(job, tenant_id="tenant-1")
        assert result is False

    async def test_cannot_accept_tenant_at_capacity(self, mgr, mock_redis):
        def side_effect(key, *a, **kw):
            if "tenant" in key:
                return 100
            return 0
        mock_redis.get = AsyncMock(side_effect=side_effect)

        job = JobCreate(job_type="pipeline.analysis", project_id="p1")
        result = await mgr.can_accept(job, tenant_id="tenant-1")
        assert result is False

    async def test_acquire_increments_counters(self, mgr, mock_redis):
        await mgr.acquire("job-1", "pipeline.analysis", "ai", "tenant-1")
        assert mock_redis.pipeline.called

    async def test_release_decrements_counters(self, mgr, mock_redis):
        await mgr.release("job-1", "pipeline.analysis", "ai", "tenant-1")
        assert mock_redis.pipeline.called

    async def test_get_usage(self, mgr, mock_redis):
        usage = await mgr.get_usage(tenant_id="tenant-1")
        assert "global_concurrent" in usage
        assert "tenant_concurrent" in usage
        assert "queues" in usage

    async def test_get_usage_without_tenant(self, mgr, mock_redis):
        usage = await mgr.get_usage()
        assert "global_concurrent" in usage
        assert "tenant_concurrent" not in usage

    async def test_reset_all(self, mgr, mock_redis):
        mock_redis.keys = AsyncMock(return_value=["resource:a", "resource:b"])
        await mgr.reset_all()
        mock_redis.delete.assert_called_once()

    async def test_ai_type_limit(self, mgr):
        job = JobCreate(job_type="ai.custom", project_id="p1")
        assert mgr._type_limit(job.job_type) == 10

    async def test_export_type_limit(self, mgr):
        job = JobCreate(job_type="export.single", project_id="p1")
        assert mgr._type_limit(job.job_type) == 5

    async def test_transcript_type_limit(self, mgr):
        job = JobCreate(job_type="pipeline.transcript", project_id="p1")
        assert mgr._type_limit(job.job_type) == 20
