"""Query Cache — caches database query results to reduce redundant queries.

Wraps query execution with result caching. Keyed by (query_string + params_hash).
Automatically invalidated on table writes. Eliminates repeated DB queries.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from typing import Any

from performance_engineering.config import PerformanceConfig

logger = logging.getLogger(__name__)


class QueryCache:
    """LRU cache for database query results.

    Caches query results by (query_string + params_hash) key.
    Supports automatic invalidation on table writes.
    Configurable TTL per query type.

    Usage::

        cache = QueryCache()
        key = cache.build_key("SELECT * FROM videos WHERE id=:id", {"id": "123"})
        result = cache.get(key)
        if not result:
            result = await db.execute(query)
            cache.set(key, result, table="videos")
        cache.invalidate_table("videos")  # After write
    """

    def __init__(self, config: PerformanceConfig | None = None) -> None:
        self._config = config or PerformanceConfig.from_env()
        self._enabled = self._config.cache_query_enabled
        self._ttl = self._config.cache_query_ttl
        self._lock = threading.Lock()
        self._cache: OrderedDict[str, tuple[float, Any, set[str]]] = OrderedDict()
        self._max_entries = 5000
        self._hits = 0
        self._misses = 0

    def build_key(self, query: str, params: dict[str, Any] | None = None) -> str:
        """Build a deterministic cache key from query + params.

        Args:
            query: SQL query string.
            params: Query parameters.

        Returns:
            SHA-256 cache key.
        """
        raw = f"{query}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Any | None:
        """Get a cached query result.

        Args:
            key: Cache key from build_key().

        Returns:
            Cached result or None.
        """
        if not self._enabled or not key:
            return None
        with self._lock:
            if key in self._cache:
                expires_at, data, _ = self._cache[key]
                if time.time() <= expires_at:
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return data
                del self._cache[key]
        self._misses += 1
        return None

    def set(
        self, key: str, data: Any,
        tables: str | list[str] | None = None,
        ttl: int | None = None,
    ) -> None:
        """Cache a query result.

        Args:
            key: Cache key from build_key().
            data: Query result data.
            tables: Table name(s) for invalidation tracking.
            ttl: Optional TTL override.
        """
        if not self._enabled or not key:
            return
        table_set = {tables} if isinstance(tables, str) else set(tables or [])
        with self._lock:
            expires_at = time.time() + (ttl or self._ttl)
            self._cache[key] = (expires_at, data, table_set)
            self._cache.move_to_end(key)
            while len(self._cache) > self._max_entries:
                self._cache.popitem(last=False)

    def invalidate_table(self, table: str) -> int:
        """Invalidate all cache entries for a table.

        Args:
            table: Table name to invalidate.

        Returns:
            Number of invalidated entries.
        """
        if not self._enabled:
            return 0
        count = 0
        with self._lock:
            keys_to_delete = [
                k for k, (_, _, tables) in self._cache.items()
                if table in tables
            ]
            for k in keys_to_delete:
                del self._cache[k]
                count += 1
        if count > 0:
            logger.debug("Query cache: invalidated %d entries for table '%s'", count, table)
        return count

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching a key pattern.

        Args:
            pattern: Substring to match in cache keys.

        Returns:
            Number of invalidated entries.
        """
        count = 0
        with self._lock:
            keys_to_delete = [k for k in self._cache if pattern in k]
            for k in keys_to_delete:
                del self._cache[k]
                count += 1
        return count

    def clear(self) -> None:
        """Clear all cached query results."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> dict[str, Any]:
        """Get query cache statistics."""
        total = self._hits + self._misses
        return {
            "cache_name": "query",
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(total, 1), 4),
            "size": len(self._cache),
            "enabled": self._enabled,
            "ttl_seconds": self._ttl,
        }
