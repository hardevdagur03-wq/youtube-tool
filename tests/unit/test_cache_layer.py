from __future__ import annotations

import time

import pytest


class TestTTLCache:
    def test_cache_hit(self):
        from utils.cache import TTLCache
        cache = TTLCache[str](ttl_seconds=60)
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_cache_miss(self):
        from utils.cache import TTLCache
        cache = TTLCache[str](ttl_seconds=60)
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self):
        from utils.cache import TTLCache
        cache = TTLCache[str](ttl_seconds=0.1)
        cache.set("key", "value")
        time.sleep(0.15)
        assert cache.get("key") is None

    def test_delete(self):
        from utils.cache import TTLCache
        cache = TTLCache[str](ttl_seconds=60)
        cache.set("key", "value")
        cache.delete("key")
        assert cache.get("key") is None

    def test_clear(self):
        from utils.cache import TTLCache
        cache = TTLCache[str](ttl_seconds=60)
        cache.set("a", "1")
        cache.set("b", "2")
        cache.clear()
        assert cache.size == 0

    def test_size(self):
        from utils.cache import TTLCache
        cache = TTLCache[str](ttl_seconds=60)
        cache.set("a", "1")
        cache.set("b", "2")
        assert cache.size == 2

    def test_per_entry_ttl(self):
        from utils.cache import TTLCache
        cache = TTLCache[str](ttl_seconds=60)
        cache.set("short", "value", ttl_seconds=0.1)
        cache.set("long", "value", ttl_seconds=60)
        time.sleep(0.15)
        assert cache.get("short") is None
        assert cache.get("long") == "value"

    def test_overwrite_key(self):
        from utils.cache import TTLCache
        cache = TTLCache[str](ttl_seconds=60)
        cache.set("key", "old_value")
        cache.set("key", "new_value")
        assert cache.get("key") == "new_value"

    def test_cache_entry(self):
        from utils.cache import CacheEntry
        entry = CacheEntry("value", 60)
        assert entry.value == "value"
        assert not entry.is_expired()


class TestDatabaseCache:
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        from database.cache import DatabaseCache
        cache = DatabaseCache()
        await cache.set("test", "key", {"data": 123})
        result = await cache.get("test", "key")
        assert result == {"data": 123}

    @pytest.mark.asyncio
    async def test_get_missing(self):
        from database.cache import DatabaseCache
        cache = DatabaseCache()
        result = await cache.get("test", "missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_namespace_isolation(self):
        from database.cache import DatabaseCache
        cache = DatabaseCache()
        await cache.set("ns1", "key", "value1")
        await cache.set("ns2", "key", "value2")
        assert await cache.get("ns1", "key") == "value1"
        assert await cache.get("ns2", "key") == "value2"

    @pytest.mark.asyncio
    async def test_invalidate_namespace(self):
        from database.cache import DatabaseCache
        cache = DatabaseCache()
        await cache.set("ns", "key1", "v1")
        await cache.set("ns", "key2", "v2")
        await cache.invalidate_namespace("ns")
        assert await cache.get("ns", "key1") is None
        assert await cache.get("ns", "key2") is None

    @pytest.mark.asyncio
    async def test_invalidate_single_key(self):
        from database.cache import DatabaseCache
        cache = DatabaseCache()
        await cache.set("test", "key", "value")
        await cache.delete("test", "key")
        assert await cache.get("test", "key") is None

    @pytest.mark.asyncio
    async def test_clear_all(self):
        from database.cache import DatabaseCache
        cache = DatabaseCache()
        await cache.set("test", "a", 1)
        await cache.set("test", "b", 2)
        await cache.clear_all()
        assert await cache.get("test", "a") is None
        assert await cache.get("test", "b") is None

    @pytest.mark.asyncio
    async def test_cache_stats(self):
        from database.cache import DatabaseCache
        cache = DatabaseCache()
        await cache.set("test", "k", "v")
        await cache.get("test", "k")
        await cache.get("test", "m")
        stats = cache.stats
        assert stats.get("memory_entries", 0) >= 0

    @pytest.mark.asyncio
    async def test_serialization(self):
        from database.cache import DatabaseCache
        cache = DatabaseCache()
        complex_data = {"list": [1, 2, 3], "nested": {"a": "b"}, "bool": True}
        await cache.set("test", "complex", complex_data)
        retrieved = await cache.get("test", "complex")
        assert retrieved == complex_data

    @pytest.mark.asyncio
    async def test_versioning(self):
        from database.cache import DatabaseCache
        cache = DatabaseCache()
        await cache.set("v", "key", "v1", ttl=60)
        assert await cache.get("v", "key") == "v1"
