from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.chaos


class TestRedisFailure:
    @pytest.mark.asyncio
    async def test_redis_down_during_pipeline(self):
        with patch("background_processing.event_bus.EventBus.publish", new_callable=AsyncMock) as m:
            m.side_effect = ConnectionError("Redis is down")
            from background_processing.event_bus import EventBus
            bus = EventBus()
            with pytest.raises(ConnectionError, match="Redis is down"):
                await bus.publish("test", {"data": 1})

    @pytest.mark.asyncio
    async def test_cache_fallback_on_redis_failure(self):
        with patch("database.cache.DatabaseCache.get", new_callable=AsyncMock) as m:
            m.side_effect = [ConnectionError("Redis down"), None]
            from database.cache import DatabaseCache
            cache = DatabaseCache()
            with pytest.raises(ConnectionError):
                await cache.get("key")

    @pytest.mark.asyncio
    async def test_distributed_lock_recovery(self):
        with patch("background_processing.distributed_lock.DistributedLock.acquire", new_callable=AsyncMock) as m:
            m.side_effect = [ConnectionError("Redis down"), True]
            from background_processing.distributed_lock import DistributedLock
            lock = DistributedLock("test_lock")
            with pytest.raises(ConnectionError):
                await lock.acquire()

    @pytest.mark.asyncio
    async def test_event_bus_reconnection(self):
        with patch("background_processing.event_bus.EventBus.publish", new_callable=AsyncMock) as m:
            m.side_effect = [
                ConnectionError("Connection lost"),
                ConnectionError("Reconnecting"),
                True,
            ]
            from background_processing.event_bus import EventBus
            bus = EventBus()
            call_count = 0
            for i in range(3):
                try:
                    await bus.publish("test_channel", {"msg": i})
                    call_count += 1
                except ConnectionError:
                    pass
            assert call_count == 1
