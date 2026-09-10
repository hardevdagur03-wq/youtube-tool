from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.cache


class TestCacheMissRate:
    @pytest.mark.asyncio
    async def test_cache_miss_triggers_computation(self):
        computation_called = False

        async def compute_value():
            nonlocal computation_called
            computation_called = True
            return {"data": "computed"}

        with patch("database.cache.DatabaseCache.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            from database.cache import DatabaseCache
            cache = DatabaseCache()
            result = await cache.get("missing_key")
            assert result is None
            computed = await compute_value()
            assert computation_called is True
            assert computed["data"] == "computed"

    @pytest.mark.asyncio
    async def test_cache_miss_populates_cache(self):
        with patch("database.cache.DatabaseCache.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [None, {"data": "now_cached"}]
            with patch("database.cache.DatabaseCache.set", new_callable=AsyncMock) as mock_set:
                mock_set.return_value = True
                from database.cache import DatabaseCache
                cache = DatabaseCache()
                result1 = await cache.get("key_to_populate")
                assert result1 is None
                await cache.set("key_to_populate", {"data": "now_cached"})
                result2 = await cache.get("key_to_populate")
                assert result2 is not None
                assert result2["data"] == "now_cached"
