"""Shared fixtures for background processing tests."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from database.base import Base
from database.config import DatabaseConfig
from database.session import DatabaseSessionManager


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest_asyncio.fixture
async def db_manager(db_path):
    mgr = DatabaseSessionManager._make_fresh()
    config = DatabaseConfig.for_testing(sqlite_path=db_path)
    mgr.initialize(config)
    await mgr.create_all()
    yield mgr
    await mgr.close()


@pytest_asyncio.fixture
async def session(db_manager):
    async with db_manager.session_factory() as s:
        yield s


@pytest_asyncio.fixture
async def job_repo(session):
    from background_processing.job_repository import JobRepository
    return JobRepository(session)


# ---------------------------------------------------------------------------
# Mock Redis fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_redis():
    """Create a mock Redis client with persistent in-memory storage."""
    _store: dict[str, str] = {}
    _lists: dict[str, list[str]] = {}

    mock = MagicMock(spec=[])

    async def _set(key, value, ex=None, nx=False, keepttl=False, **kw):
        if nx and key in _store:
            return False
        _store[key] = value if isinstance(value, str) else str(value)
        return True

    async def _get(key):
        return _store.get(key)

    async def _delete(*keys):
        count = 0
        for k in keys:
            if k in _store:
                del _store[k]
                count += 1
        return count

    async def _exists(key):
        return 1 if key in _store else 0

    async def _keys(pattern=""):
        if pattern and pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in _store if k.startswith(prefix)]
        return list(_store.keys())

    async def _hmget(key, *fields):
        val = _store.get(key, "")
        import json
        try:
            data = json.loads(val) if isinstance(val, str) else val
            return [data.get(f, "") for f in fields]
        except (json.JSONDecodeError, TypeError):
            return [""] * len(fields)

    async def _lpush(key, value):
        if key not in _lists:
            _lists[key] = []
        _lists[key].insert(0, value)
        return len(_lists[key])

    async def _lrange(key, start, stop):
        lst = _lists.get(key, [])
        return lst[start:stop + 1] if stop >= 0 else lst[start:]

    async def _llen(key):
        return len(_lists.get(key, []))

    async def _lrem(key, count, value):
        lst = _lists.get(key, [])
        removed = 0
        for _ in range(count):
            if value in lst:
                lst.remove(value)
                removed += 1
        return removed

    async def _ltrim(key, start, stop):
        lst = _lists.get(key, [])
        _lists[key] = lst[start:stop + 1] if stop >= 0 else lst[start:]
        return True

    async def _eval(script, num_keys, *args):
        return 1

    async def _ping():
        return True

    async def _publish(channel, message):
        return 1

    async def _pubsub_numsub(channel):
        return {channel: 0}

    mock.set = AsyncMock(side_effect=_set)
    mock.get = AsyncMock(side_effect=_get)
    mock.delete = AsyncMock(side_effect=_delete)
    mock.exists = AsyncMock(side_effect=_exists)
    mock.expire = AsyncMock(return_value=True)
    mock.publish = AsyncMock(side_effect=_publish)
    mock.ping = AsyncMock(side_effect=_ping)
    mock.lpush = AsyncMock(side_effect=_lpush)
    mock.lrange = AsyncMock(side_effect=_lrange)
    mock.llen = AsyncMock(side_effect=_llen)
    mock.lrem = AsyncMock(side_effect=_lrem)
    mock.ltrim = AsyncMock(side_effect=_ltrim)
    mock.keys = AsyncMock(side_effect=_keys)
    mock.eval = AsyncMock(side_effect=_eval)
    mock.hmget = AsyncMock(side_effect=_hmget)
    mock.wait = AsyncMock(return_value=None)

    class _MockPipeline:
        def __init__(self):
            self._commands = []
        def incr(self, key):
            self._commands.append(("incr", key))
            return self
        def decr(self, key):
            self._commands.append(("decr", key))
            return self
        def expire(self, key, ttl):
            self._commands.append(("expire", key, ttl))
            return self
        async def execute(self):
            return [1] * len(self._commands)

    def _pipeline():
        return _MockPipeline()

    mock.pipeline = MagicMock(side_effect=_pipeline)
    mock.pubsub = MagicMock()
    pubsub_instance = MagicMock()
    pubsub_instance.psubscribe = AsyncMock(return_value=None)
    pubsub_instance.punsubscribe = AsyncMock(return_value=None)
    pubsub_instance.close = AsyncMock(return_value=None)
    mock.pubsub.return_value = pubsub_instance
    mock.pubsub_numsub = AsyncMock(side_effect=_pubsub_numsub)
    mock.aclose = AsyncMock(return_value=None)

    def from_url_side_effect(*args, **kwargs):
        return mock

    with patch("redis.asyncio.Redis.from_url", side_effect=from_url_side_effect):
        yield mock


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_job_data():
    return {
        "job_type": "pipeline.analysis",
        "project_id": "proj-123",
        "queue": "default",
        "priority": "normal",
        "max_retries": 3,
        "payload": {"key": "value"},
    }


@pytest.fixture
def sample_project():
    return {
        "project_id": "proj-test-001",
        "name": "Test Project",
        "video_id": "vid123",
        "url": "https://youtube.com/watch?v=vid123",
        "status": "created",
    }
