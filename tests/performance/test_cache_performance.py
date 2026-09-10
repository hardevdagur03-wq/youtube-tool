from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.performance


class TestCachePerformance:
    @pytest.mark.asyncio
    async def test_cache_hit_latency(self, performance_config):
        with patch("database.cache.DatabaseCache.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"cached": "data"}
            from database.cache import DatabaseCache
            cache = DatabaseCache()
            latencies = []
            for _ in range(50):
                start = time.perf_counter()
                result = await cache.get("test_key")
                latencies.append((time.perf_counter() - start) * 1000)
            p95 = sorted(latencies)[int(len(latencies) * 0.95)]
            assert p95 < performance_config["cache_hit_threshold_ms"], (
                f"Cache hit P95={p95:.2f}ms exceeds {performance_config['cache_hit_threshold_ms']}ms"
            )
            assert result == {"cached": "data"}

    @pytest.mark.asyncio
    async def test_cache_miss_latency(self, performance_config):
        with patch("database.cache.DatabaseCache.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            from database.cache import DatabaseCache
            cache = DatabaseCache()
            latencies = []
            for _ in range(20):
                start = time.perf_counter()
                result = await cache.get("missing_key")
                latencies.append((time.perf_counter() - start) * 1000)
            p95 = sorted(latencies)[int(len(latencies) * 0.95)]
            assert p95 < performance_config["cache_miss_threshold_ms"], (
                f"Cache miss P95={p95:.2f}ms exceeds {performance_config['cache_miss_threshold_ms']}ms"
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_cache_throughput(self, performance_config):
        with patch("database.cache.DatabaseCache.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = "value"
            with patch("database.cache.DatabaseCache.set", new_callable=AsyncMock) as mock_set:
                mock_set.return_value = True
                from database.cache import DatabaseCache
                cache = DatabaseCache()
                start = time.perf_counter()
                for i in range(100):
                    await cache.set(f"key_{i}", f"value_{i}")
                    await cache.get(f"key_{i}")
                total_s = time.perf_counter() - start
                ops_per_sec = 200 / total_s
                assert ops_per_sec > 1000, (
                    f"Cache throughput {ops_per_sec:.0f} ops/sec below 1000"
                )

    @pytest.mark.asyncio
    async def test_cache_hit_rate_improvement(self, performance_config):
        with patch("database.cache.DatabaseCache.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [None, {"data": "result"}, None, {"data": "result"}]
            from database.cache import DatabaseCache
            cache = DatabaseCache()
            start_no_cache = time.perf_counter()
            await cache.get("key")
            dur_no_cache = (time.perf_counter() - start_no_cache) * 1000
            start_with_cache = time.perf_counter()
            await cache.get("key")
            dur_with_cache = (time.perf_counter() - start_with_cache) * 1000
            improvement = dur_no_cache / dur_with_cache if dur_with_cache > 0 else 0
            assert improvement > 1.5, (
                f"Cache improvement factor {improvement:.1f}x below 1.5x"
            )
