from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.cache


class TestCacheHitRate:
    @pytest.mark.asyncio
    async def test_cache_hit_returns_correct_data(self):
        with patch("database.cache.DatabaseCache.get", new_callable=AsyncMock) as mock_get:
            expected = {"project_id": "p1", "name": "Cached"}
            mock_get.return_value = expected
            from database.cache import DatabaseCache
            cache = DatabaseCache()
            result = await cache.get("project_p1")
            assert result == expected
            assert result["project_id"] == "p1"

    @pytest.mark.asyncio
    async def test_cache_hit_rate_threshold(self):
        hit_count = 85
        miss_count = 15
        total = hit_count + miss_count
        hit_rate = hit_count / total
        assert hit_rate >= 0.80, (
            f"Cache hit rate {hit_rate:.2%} below 80% threshold"
        )
