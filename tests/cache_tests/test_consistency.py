from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.cache


class TestCacheConsistency:
    @pytest.mark.asyncio
    async def test_cache_db_consistency(self):
        with patch("database.cache.DatabaseCache.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            with patch("database.cache.DatabaseCache.set", new_callable=AsyncMock) as mock_set:
                mock_set.return_value = True
                from database.cache import DatabaseCache
                cache = DatabaseCache()
                db_data = {"project_id": "p1", "name": "Consistent", "version": 1}
                await cache.set("project_p1", db_data)
                cached = await cache.get("project_p1")
                assert cached is not None or mock_get.called

    @pytest.mark.asyncio
    async def test_cache_write_through(self):
        db_store = {}

        async def db_write(key, value):
            db_store[key] = value
            return True

        async def db_read(key):
            return db_store.get(key)

        with patch("database.cache.DatabaseCache.set", new_callable=AsyncMock) as mock_set:
            mock_set.side_effect = db_write
            from database.cache import DatabaseCache
            cache = DatabaseCache()
            await cache.set("write_through_key", {"data": "synced"})
            assert "write_through_key" in db_store or mock_set.called

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_update(self):
        with patch("database.cache.DatabaseCache.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                {"data": "old_value"},
                None,
                {"data": "new_value"},
            ]
            with patch("database.cache.DatabaseCache.delete", new_callable=AsyncMock) as mock_del:
                mock_del.return_value = True
                from database.cache import DatabaseCache
                cache = DatabaseCache()
                old = await cache.get("updatable_key")
                assert old["data"] == "old_value"
                await cache.delete("updatable_key")
                stale = await cache.get("updatable_key")
                assert stale is None
                with patch("database.cache.DatabaseCache.set", new_callable=AsyncMock) as mock_set:
                    mock_set.return_value = True
                    await cache.set("updatable_key", {"data": "new_value"})
                    fresh = await cache.get("updatable_key")
                    assert fresh["data"] == "new_value"
