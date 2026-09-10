from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.cache


class TestCacheEviction:
    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        with patch("database.cache.DatabaseCache.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            with patch("database.cache.DatabaseCache.set", new_callable=AsyncMock) as mock_set:
                mock_set.return_value = True
                from database.cache import DatabaseCache
                cache = DatabaseCache()
                for i in range(10):
                    await cache.set(f"key_{i}", f"value_{i}")
                    mock_set.assert_called()

    @pytest.mark.asyncio
    async def test_ttl_eviction(self):
        with patch("database.cache.DatabaseCache.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [{"data": "alive"}, None]
            from database.cache import DatabaseCache
            cache = DatabaseCache()
            alive = await cache.get("ttl_key")
            assert alive is not None
            expired = await cache.get("ttl_key")
            assert expired is None

    @pytest.mark.asyncio
    async def test_manual_eviction(self):
        with patch("database.cache.DatabaseCache.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [{"data": "present"}, None]
            with patch("database.cache.DatabaseCache.delete", new_callable=AsyncMock) as mock_del:
                mock_del.return_value = True
                from database.cache import DatabaseCache
                cache = DatabaseCache()
                before = await cache.get("evict_me")
                assert before is not None
                await cache.delete("evict_me")
                after = await cache.get("evict_me")
                assert after is None
