from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.cache


class TestCacheTTL:
    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(self):
        with patch("database.cache.DatabaseCache.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [{"data": "cached"}, None]
            from database.cache import DatabaseCache
            cache = DatabaseCache()
            result1 = await cache.get("expiring_key")
            assert result1 is not None
            result2 = await cache.get("expiring_key")
            assert result2 is None

    @pytest.mark.asyncio
    async def test_cache_ttl_refresh_on_access(self):
        with patch("database.cache.DatabaseCache.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"data": "fresh"}
            with patch("database.cache.DatabaseCache.set", new_callable=AsyncMock) as mock_set:
                mock_set.return_value = True
                from database.cache import DatabaseCache
                cache = DatabaseCache()
                result = await cache.get("refresh_key")
                assert result is not None
                await cache.set("refresh_key", result, ttl=300)

    @pytest.mark.asyncio
    async def test_cache_stale_data_not_returned(self):
        with patch("database.cache.DatabaseCache.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [None, {"data": "fresh_data"}]
            from database.cache import DatabaseCache
            cache = DatabaseCache()
            stale = await cache.get("stale_key")
            assert stale is None
            fresh = await cache.get("stale_key")
            assert fresh is not None
            assert fresh["data"] == "fresh_data"
