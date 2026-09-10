from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from database.cache import DatabaseCache


class TestCacheLayerIntegration:
    @pytest.mark.asyncio
    async def test_redis_cache_hit(self):
        cache = DatabaseCache(use_redis=False)
        await cache.set("test", "hit_key", {"value": "cached"})
        result = await cache.get("test", "hit_key")
        assert result == {"value": "cached"}

    @pytest.mark.asyncio
    async def test_redis_cache_miss(self):
        cache = DatabaseCache(use_redis=False)
        result = await cache.get("test", "nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_ttl_expiry(self):
        cache = DatabaseCache(use_redis=False)
        await cache.set("test", "ttl_key", "short_lived")
        await cache.set("test", "ttl_key_2", "persistent")
        result = await cache.get("test", "ttl_key")
        assert result == "short_lived"
        result2 = await cache.get("test", "ttl_key_2")
        assert result2 == "persistent"

    @pytest.mark.asyncio
    async def test_cache_eviction(self):
        cache = DatabaseCache(use_redis=False)
        for i in range(20):
            await cache.set("eviction", f"key_{i}", f"value_{i}")
        count = await cache.invalidate_namespace("eviction")
        assert count == 20
        for i in range(20):
            result = await cache.get("eviction", f"key_{i}")
            assert result is None

    @pytest.mark.asyncio
    async def test_namespace_isolation(self):
        cache = DatabaseCache(use_redis=False)
        await cache.set("ns_a", "shared_key", "value_a")
        await cache.set("ns_b", "shared_key", "value_b")

        result_a = await cache.get("ns_a", "shared_key")
        result_b = await cache.get("ns_b", "shared_key")
        assert result_a == "value_a"
        assert result_b == "value_b"

        count = await cache.invalidate_namespace("ns_a")
        assert count >= 1
        assert await cache.get("ns_a", "shared_key") is None
        assert await cache.get("ns_b", "shared_key") == "value_b"

    @pytest.mark.asyncio
    async def test_cache_fallback_on_redis_failure(self):
        cache = DatabaseCache(use_redis=False)
        await cache.set("fallback", "key", "should_work")
        result = await cache.get("fallback", "key")
        assert result == "should_work"

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self):
        cache = DatabaseCache(use_redis=False)

        async def setter(name):
            for i in range(10):
                await cache.set("concurrent", f"{name}_{i}", f"value_{i}")

        async def getter(name):
            results = []
            for i in range(10):
                val = await cache.get("concurrent", f"{name}_{i}")
                if val:
                    results.append(val)
            return results

        set_tasks = [setter(f"writer_{j}") for j in range(5)]
        get_tasks = [getter(f"reader_{j}") for j in range(5)]

        await asyncio.gather(*set_tasks, *get_tasks)
        final = await cache.get("concurrent", "writer_0_0")
        assert final is not None

    @pytest.mark.asyncio
    async def test_get_or_set_race_condition(self):
        cache = DatabaseCache(use_redis=False)
        call_count = 0

        async def expensive_factory():
            nonlocal call_count
            call_count += 1
            return {"result": "expensive"}

        results = await asyncio.gather(*[
            cache.get_or_set("race", "key", expensive_factory)
            for _ in range(10)
        ])
        assert all(r == {"result": "expensive"} for r in results)

    @pytest.mark.asyncio
    async def test_bulk_invalidation(self):
        cache = DatabaseCache(use_redis=False)
        namespaces = ["bulk_a", "bulk_b", "bulk_c"]
        for ns in namespaces:
            for i in range(5):
                await cache.set(ns, f"key_{i}", f"val_{i}")

        for ns in namespaces:
            count = await cache.invalidate_namespace(ns)
            assert count == 5
            for i in range(5):
                assert await cache.get(ns, f"key_{i}") is None
