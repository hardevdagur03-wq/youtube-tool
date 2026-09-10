from __future__ import annotations

import json
import logging
import time
from threading import Lock
from typing import Any, Generic, TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


class CacheEntry:
    __slots__ = ("value", "expires_at", "created_at", "hit_count")

    def __init__(self, value: Any, ttl_seconds: float) -> None:
        self.value = value
        self.expires_at = time.time() + ttl_seconds
        self.created_at = time.time()
        self.hit_count = 0

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def record_hit(self) -> None:
        self.hit_count += 1


class TTLCache(Generic[T]):
    """Thread-safe in-memory TTL cache with bounded size and O(1) eviction."""

    def __init__(self, ttl_seconds: float = 300, max_size: int = 10000) -> None:
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._store: dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> T | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired():
                del self._store[key]
                self._misses += 1
                return None
            self._hits += 1
            entry.record_hit()
            return entry.value

    def set(self, key: str, value: T, ttl_seconds: float | None = None) -> None:
        with self._lock:
            if len(self._store) >= self._max_size:
                self._evict_one()
            self._store[key] = CacheEntry(value, ttl_seconds or self._ttl)

    def _evict_one(self) -> None:
        if not self._store:
            return
        oldest_key = min(self._store.keys(), key=lambda k: self._store[k].created_at)
        self._store.pop(oldest_key, None)
        self._evictions += 1

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    @property
    def hit_ratio(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def evictions(self) -> int:
        return self._evictions


class RedisCache(Generic[T]):
    """Redis-backed cache with TTL support and in-memory fallback."""

    def __init__(self, ttl_seconds: float = 86400) -> None:
        self._ttl = ttl_seconds
        self._redis = None
        self._fallback = TTLCache[T](ttl_seconds=ttl_seconds)
        self._use_redis = False
        self._redis_checked = False
        self._hits = 0
        self._misses = 0

    def _ensure_redis(self) -> bool:
        if self._redis_checked:
            return self._use_redis
        self._redis_checked = True
        try:
            import redis as redis_module
            from config.settings import settings
            self._redis = redis_module.Redis.from_url(
                settings.redis_url,
                socket_connect_timeout=2,
                socket_timeout=2,
                decode_responses=True,
            )
            self._redis.ping()
            self._use_redis = True
            logger.info("Redis cache connected: %s", settings.redis_url)
        except Exception:
            self._use_redis = False
            logger.warning("Redis unavailable, using in-memory fallback cache")
        return self._use_redis

    def get(self, key: str) -> T | None:
        if self._ensure_redis():
            try:
                val = self._redis.get(key)
                if val is not None:
                    self._hits += 1
                    return json.loads(val)
                self._misses += 1
                return None
            except Exception:
                pass
        return self._fallback.get(key)

    def set(self, key: str, value: T, ttl_seconds: float | None = None) -> None:
        ttl = ttl_seconds or self._ttl
        if self._ensure_redis():
            try:
                self._redis.setex(key, int(ttl), json.dumps(value, default=str))
                return
            except Exception:
                pass
        self._fallback.set(key, value, ttl)

    def delete(self, key: str) -> None:
        if self._ensure_redis():
            try:
                self._redis.delete(key)
                return
            except Exception:
                pass
        self._fallback.delete(key)

    def clear(self) -> None:
        if self._ensure_redis():
            try:
                self._redis.flushdb()
                return
            except Exception:
                pass
        self._fallback.clear()

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": round(self._hits / (self._hits + self._misses), 3) if (self._hits + self._misses) > 0 else 0,
            "using_redis": self._use_redis,
            "fallback_size": self._fallback.size,
        }


class CacheService:
    """Centralized caching for YouTube API responses."""

    def __init__(self) -> None:
        self.channel_handle = TTLCache[dict](ttl_seconds=86400)
        self.channel_id = TTLCache[dict](ttl_seconds=86400)
        self.playlist_id = TTLCache[str](ttl_seconds=86400)
        self.video_metadata = TTLCache[dict](ttl_seconds=600)
        self.channel_title = TTLCache[str](ttl_seconds=86400)
        self.export_history = TTLCache[list](ttl_seconds=3600)
        self._total_hits = 0
        self._total_misses = 0

    def _hit(self) -> None:
        self._total_hits += 1

    def _miss(self) -> None:
        self._total_misses += 1

    def get_channel_by_handle(self, handle: str) -> dict | None:
        result = self.channel_handle.get(handle.lower())
        if result is not None:
            self._hit()
        else:
            self._miss()
        return result

    def set_channel_by_handle(self, handle: str, data: dict) -> None:
        self.channel_handle.set(handle.lower(), data)

    def get_channel_by_id(self, channel_id: str) -> dict | None:
        result = self.channel_id.get(channel_id)
        if result is not None:
            self._hit()
        else:
            self._miss()
        return result

    def set_channel_by_id(self, channel_id: str, data: dict) -> None:
        self.channel_id.set(channel_id, data)

    def get_playlist_id(self, channel_id: str) -> str | None:
        result = self.playlist_id.get(channel_id)
        if result is not None:
            self._hit()
        else:
            self._miss()
        return result

    def set_playlist_id(self, channel_id: str, playlist_id: str) -> None:
        self.playlist_id.set(channel_id, playlist_id)

    def get_video_metadata(self, video_id: str) -> dict | None:
        result = self.video_metadata.get(video_id)
        if result is not None:
            self._hit()
        else:
            self._miss()
        return result

    def set_video_metadata(self, video_id: str, data: dict) -> None:
        self.video_metadata.set(video_id, data)

    def get_channel_title(self, channel_id: str) -> str | None:
        return self.channel_title.get(channel_id)

    def set_channel_title(self, channel_id: str, title: str) -> None:
        self.channel_title.set(channel_id, title)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_hits": self._total_hits,
            "total_misses": self._total_misses,
            "hit_ratio": round(self._total_hits / (self._total_hits + self._total_misses), 3) if (self._total_hits + self._total_misses) > 0 else 0,
            "channel_handle_cache_size": self.channel_handle.size,
            "channel_id_cache_size": self.channel_id.size,
            "playlist_id_cache_size": self.playlist_id.size,
            "video_metadata_cache_size": self.video_metadata.size,
        }


cache_service = CacheService()
