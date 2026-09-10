"""Tests for the Idempotency Engine — duplicate detection and prevention."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from background_processing.idempotency import DedupResult, IdempotencyEngine


class TestIdempotencyEngine:
    @pytest_asyncio.fixture
    async def engine(self, mock_redis):
        eng = IdempotencyEngine(redis_client=mock_redis)
        yield eng

    async def test_check_no_duplicate(self, engine):
        key = f"idempotent:{engine._hash_key('project:123:pipeline.analysis')}"
        result = await engine.check("project:123:pipeline.analysis")
        assert result.is_duplicate is False
        assert result.existing_job_id == ""

    async def test_check_duplicate_detected(self, engine, mock_redis):
        await engine.record("project:123:pipeline.analysis", "job-123", ttl=3600)
        result = await engine.check("project:123:pipeline.analysis")
        assert result.is_duplicate is True
        assert result.existing_job_id == "job-123"

    async def test_record_job_key(self, engine, mock_redis):
        await engine.record("project:123:pipeline.analysis", "job-123", ttl=3600)
        key = f"idempotent:{engine._hash_key('project:123:pipeline.analysis')}"
        stored = await mock_redis.get(key)
        assert stored is not None
        data = json.loads(stored)
        assert data["job_id"] == "job-123"

    async def test_release_job_key(self, engine, mock_redis):
        await engine.record("project:123:pipeline.analysis", "job-123", ttl=3600)
        await engine.release("project:123:pipeline.analysis")
        key = f"idempotent:{engine._hash_key('project:123:pipeline.analysis')}"
        stored = await mock_redis.get(key)
        assert stored is None

    async def test_update_status(self, engine, mock_redis):
        await engine.record("project:123:pipeline.analysis", "job-123", ttl=3600)
        await engine.update_status("project:123:pipeline.analysis", "completed")
        key = f"idempotent:{engine._hash_key('project:123:pipeline.analysis')}"
        stored = await mock_redis.get(key)
        assert stored is not None
        data = json.loads(stored)
        assert data["status"] == "completed"

    async def test_different_keys_not_duplicates(self, engine):
        r1 = await engine.check("project:1:pipeline.a")
        r2 = await engine.check("project:2:pipeline.b")
        assert r1.is_duplicate is False
        assert r2.is_duplicate is False

    async def test_same_key_different_payload_not_duplicate(self, engine):
        key1 = "proj-1:pipeline.analysis:{\"video\":\"a\"}"
        key2 = "proj-1:pipeline.analysis:{\"video\":\"b\"}"
        r1 = await engine.check(key1)
        r2 = await engine.check(key2)
        assert r1.is_duplicate is False
        assert r2.is_duplicate is False
