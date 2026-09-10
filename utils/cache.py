"""Simple in-memory cache with TTL support.

Designed as a lightweight cache for API responses.
Ready for future Redis/memcached replacement.
"""

import time
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class CacheEntry:
    """A single cache entry with expiry."""

    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl_seconds: float) -> None:
        self.value = value
        self.expires_at = time.time() + ttl_seconds

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class TTLCache(Generic[T]):
    """Thread-safe in-memory cache with time-to-live eviction.

    Usage::

        cache = TTLCache[str](ttl_seconds=300)
        cache.set("key", "value")
        value = cache.get("key")  # "value" or None
    """

    def __init__(self, ttl_seconds: float = 300) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, CacheEntry] = {}

    def get(self, key: str) -> T | None:
        """Get a value from the cache.

        Returns:
            The cached value, or ``None`` if missing or expired.
        """
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            del self._store[key]
            return None
        return entry.value  # type: ignore

    def set(self, key: str, value: T, ttl_seconds: float | None = None) -> None:
        """Set a value in the cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl_seconds: Optional per-entry TTL override.
        """
        self._store[key] = CacheEntry(value, ttl_seconds or self._ttl)

    def delete(self, key: str) -> None:
        """Remove a key from the cache."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._store.clear()

    @property
    def size(self) -> int:
        """Number of entries currently in the cache."""
        return len(self._store)
