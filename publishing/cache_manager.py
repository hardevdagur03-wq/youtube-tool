from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from publishing.models import ExportCacheEntry

logger = logging.getLogger(__name__)

MEMORY_CACHE: dict[str, ExportCacheEntry] = {}
DEFAULT_TTL = 3600


class CacheManager:
    def __init__(self, ttl: int = DEFAULT_TTL, use_redis: bool = False):
        self.ttl = ttl
        self._use_redis = use_redis
        self._redis = None
        self._memory = MEMORY_CACHE

        if use_redis:
            self._init_redis()

    def _init_redis(self) -> None:
        try:
            import redis as redis_lib
            self._redis = redis_lib.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_CACHE_DB", "0")),
                decode_responses=True,
            )
            self._redis.ping()
            logger.info("Connected to Redis for export caching")
        except Exception as e:
            logger.warning("Redis unavailable, falling back to memory cache: %s", e)
            self._use_redis = False
            self._redis = None

    def cache_key(self, project_id: str, fmt: str, version: int = 0) -> str:
        return f"export:{project_id}:{fmt}:{version}"

    def get(self, project_id: str, fmt: str, version: int = 0) -> ExportCacheEntry | None:
        key = self.cache_key(project_id, fmt, version)
        if self._use_redis and self._redis:
            try:
                data = self._redis.get(key)
                if data:
                    entry = ExportCacheEntry(**json.loads(data))
                    if not self._is_expired(entry):
                        return entry
                    self._redis.delete(key)
            except Exception as e:
                logger.warning("Redis get failed: %s", e)

        entry = self._memory.get(key)
        if entry and not self._is_expired(entry):
            return entry
        if entry:
            del self._memory[key]
        return None

    def set(self, project_id: str, fmt: str, file_info: dict[str, Any],
            version: int = 0) -> ExportCacheEntry:
        key = self.cache_key(project_id, fmt, version)
        entry = ExportCacheEntry(
            key=key,
            project_id=project_id,
            format=fmt,
            version=version,
            file_info=file_info,
            created_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            ttl=self.ttl,
        )

        if self._use_redis and self._redis:
            try:
                self._redis.setex(key, self.ttl, entry.model_dump_json())
            except Exception as e:
                logger.warning("Redis set failed: %s", e)

        self._memory[key] = entry
        return entry

    def invalidate(self, project_id: str, fmt: str | None = None,
                   version: int | None = None) -> int:
        count = 0
        pattern = f"export:{project_id}:"
        if fmt:
            pattern += f"{fmt}:"
            if version is not None:
                pattern += f"{version}"
            else:
                pattern += "*"
        else:
            pattern += "*"

        if self._use_redis and self._redis:
            try:
                cursor = 0
                while True:
                    cursor, keys = self._redis.scan(cursor, match=pattern, count=100)
                    if keys:
                        self._redis.delete(*keys)
                        count += len(keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning("Redis invalidation failed: %s", e)

        memory_keys = [k for k in self._memory if self._key_matches(k, project_id, fmt, version)]
        for k in memory_keys:
            del self._memory[k]
            count += 1

        return count

    def exists(self, project_id: str, fmt: str, version: int = 0) -> bool:
        return self.get(project_id, fmt, version) is not None

    def clear_all(self) -> int:
        count = 0
        if self._use_redis and self._redis:
            try:
                cursor = 0
                while True:
                    cursor, keys = self._redis.scan(cursor, match="export:*", count=100)
                    if keys:
                        self._redis.delete(*keys)
                        count += len(keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning("Redis clear failed: %s", e)

        count += len(self._memory)
        self._memory.clear()
        return count

    def _is_expired(self, entry: ExportCacheEntry) -> bool:
        if entry.ttl <= 0:
            return False
        created = __import__("datetime").datetime.fromisoformat(entry.created_at)
        elapsed = (__import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ) - created).total_seconds()
        return elapsed > entry.ttl

    @staticmethod
    def _key_matches(key: str, project_id: str, fmt: str | None,
                     version: int | None) -> bool:
        parts = key.split(":")
        if len(parts) < 3:
            return False
        if parts[1] != project_id:
            return False
        if fmt and parts[2] != fmt:
            return False
        if version is not None and len(parts) > 3:
            try:
                return int(parts[3]) == version
            except ValueError:
                return False
        return True
