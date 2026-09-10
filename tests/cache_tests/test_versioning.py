from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.cache


class TestCacheVersioning:
    @pytest.mark.asyncio
    async def test_cache_version_isolation(self):
        with patch("database.cache.DatabaseCache.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                {"version": 1, "data": "v1"},
                {"version": 2, "data": "v2"},
            ]
            from database.cache import DatabaseCache
            cache = DatabaseCache()
            v1_data = await cache.get("versioned_key")
            assert v1_data["version"] == 1
            v2_data = await cache.get("versioned_key")
            assert v2_data["version"] == 2
            assert v1_data != v2_data

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_version_change(self):
        with patch("database.cache.DatabaseCache.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                {"version": 1, "data": "old"},
                None,
                {"version": 2, "data": "new"},
            ]
            with patch("database.cache.DatabaseCache.set", new_callable=AsyncMock) as mock_set:
                mock_set.return_value = True
                from database.cache import DatabaseCache
                cache = DatabaseCache()
                old = await cache.get("versioned_key")
                assert old["version"] == 1
                await cache.set("versioned_key", {"version": 2, "data": "new"})
                result = await cache.get("versioned_key")
                assert result is not None
                assert result["version"] == 2
                assert result["data"] == "new"
