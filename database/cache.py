from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

MEMORY_CACHE: dict[str, "CacheEntry"] = {}


class CacheEntry:
    def __init__(self, key: str, value: Any, ttl: int):
        self.key = key
        self.value = value
        self.ttl = ttl
        self.created_at = time.time()

    @property
    def is_expired(self) -> bool:
        if self.ttl <= 0:
            return False
        return (time.time() - self.created_at) > self.ttl


class DatabaseCache:
    def __init__(self, use_redis: bool = False, default_ttl: int = 300):
        self._use_redis = use_redis
        self._default_ttl = default_ttl
        self._redis = None
        self._prefix = "yt_blog:db:"

        if use_redis:
            self._init_redis()

    def _init_redis(self) -> None:
        try:
            import redis as redis_lib
            self._redis = redis_lib.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_CACHE_DB", "1")),
                decode_responses=True,
            )
            self._redis.ping()
            logger.info("Database cache connected to Redis")
        except Exception as e:
            logger.warning("Redis unavailable for database cache: %s", e)
            self._use_redis = False

    def _make_key(self, namespace: str, identifier: str) -> str:
        raw = f"{self._prefix}{namespace}:{identifier}"
        if len(raw) > 200:
            return f"{self._prefix}{namespace}:" + hashlib.sha256(raw.encode()).hexdigest()[:32]
        return raw

    async def get(self, namespace: str, identifier: str) -> Any | None:
        key = self._make_key(namespace, identifier)

        if self._use_redis and self._redis:
            try:
                data = self._redis.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.warning("Redis cache get failed: %s", e)

        entry = MEMORY_CACHE.get(key)
        if entry and not entry.is_expired:
            return entry.value
        if entry:
            del MEMORY_CACHE[key]
        return None

    async def set(
        self,
        namespace: str,
        identifier: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        key = self._make_key(namespace, identifier)
        ttl = ttl if ttl is not None else self._default_ttl
        serialized = json.dumps(value, default=str)

        if self._use_redis and self._redis:
            try:
                self._redis.setex(key, ttl, serialized)
            except Exception as e:
                logger.warning("Redis cache set failed: %s", e)

        MEMORY_CACHE[key] = CacheEntry(key, value, ttl)

    async def delete(self, namespace: str, identifier: str) -> bool:
        key = self._make_key(namespace, identifier)

        if self._use_redis and self._redis:
            try:
                self._redis.delete(key)
            except Exception as e:
                logger.warning("Redis cache delete failed: %s", e)

        return MEMORY_CACHE.pop(key, None) is not None

    async def invalidate_namespace(self, namespace: str) -> int:
        count = 0
        pattern = self._make_key(namespace, "*")

        if self._use_redis and self._redis:
            try:
                cursor = 0
                search_prefix = self._prefix + namespace
                while True:
                    cursor, keys = self._redis.scan(
                        cursor, match=f"{search_prefix}:*", count=100
                    )
                    if keys:
                        self._redis.delete(*keys)
                        count += len(keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning("Redis namespace invalidation failed: %s", e)

        prefix = f"{self._prefix}{namespace}:"
        memory_keys = [k for k in MEMORY_CACHE if k.startswith(prefix)]
        for k in memory_keys:
            del MEMORY_CACHE[k]
            count += 1

        return count

    async def invalidate_project(self, project_uuid: str) -> int:
        total = 0
        for ns in [
            "project", "video", "transcript", "analysis",
            "knowledge_graph", "seo", "outline", "section",
            "draft", "review", "optimization", "export",
        ]:
            total += await self.invalidate_namespace(f"{ns}:{project_uuid[:8]}")
        return total

    async def get_or_set(
        self,
        namespace: str,
        identifier: str,
        factory,
        ttl: int | None = None,
    ) -> Any:
        cached = await self.get(namespace, identifier)
        if cached is not None:
            return cached

        value = await factory()
        await self.set(namespace, identifier, value, ttl)
        return value

    async def clear_all(self) -> int:
        count = 0

        if self._use_redis and self._redis:
            try:
                cursor = 0
                while True:
                    cursor, keys = self._redis.scan(
                        cursor, match=f"{self._prefix}*", count=100
                    )
                    if keys:
                        self._redis.delete(*keys)
                        count += len(keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning("Redis flush failed: %s", e)

        count += len(MEMORY_CACHE)
        MEMORY_CACHE.clear()
        return count

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "memory_entries": len(MEMORY_CACHE),
            "redis_connected": self._use_redis and self._redis is not None,
        }


db_cache = DatabaseCache()
