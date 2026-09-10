"""Cache Manager — caches optimization prompts, sections, and validation results."""

from __future__ import annotations
import hashlib
import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)


class OptimizationCacheManager:
    """TTL-based cache for optimization artifacts."""

    def __init__(self, cache_dir: str = "output/cache", default_ttl: int = 3600):
        self._cache_dir = cache_dir
        self._default_ttl = default_ttl
        self._memory_cache: dict[str, dict] = {}
        self._invalidated: set[str] = set()
        self._hits: int = 0
        self._misses: int = 0
        os.makedirs(cache_dir, exist_ok=True)

    def get(self, key: str) -> Any | None:
        # Check memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if time.time() - entry["timestamp"] < entry.get("ttl", self._default_ttl):
                self._hits += 1
                logger.debug("[CacheManager] Memory hit for key %s...", key[:40])
                return entry["value"]
            else:
                del self._memory_cache[key]

        # Check disk cache (skip if invalidated)
        if key in self._invalidated:
            self._invalidated.discard(key)
            self._misses += 1
            return None

        filepath = self._key_to_path(key)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    entry = json.load(f)
                if time.time() - entry["timestamp"] < entry.get("ttl", self._default_ttl):
                    self._hits += 1
                    value = entry["value"]
                    self._memory_cache[key] = {"value": value, "timestamp": entry["timestamp"], "ttl": entry.get("ttl")}
                    logger.debug("[CacheManager] Disk hit for key %s...", key[:40])
                    return value
                else:
                    os.remove(filepath)
            except Exception as exc:
                logger.debug("[CacheManager] Cache read error: %s", exc)

        self._misses += 1
        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        entry = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl or self._default_ttl,
        }
        self._memory_cache[key] = entry

        filepath = self._key_to_path(key)
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(entry, f, indent=2, default=str)
        except Exception as exc:
            logger.debug("[CacheManager] Cache write error: %s", exc)

    def get_or_compute(self, key: str, compute_fn, ttl: int | None = None) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = compute_fn()
        self.set(key, value, ttl)
        return value

    def invalidate(self, key_prefix: str) -> None:
        keys_to_delete = [k for k in self._memory_cache if k.startswith(key_prefix) or key_prefix in k]
        for k in keys_to_delete:
            del self._memory_cache[k]
            self._invalidated.add(k)

        cache_dir = self._cache_dir
        if os.path.exists(cache_dir):
            for fname in os.listdir(cache_dir):
                if fname.endswith('.json'):
                    fpath = os.path.join(cache_dir, fname)
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            content = f.read(200)
                        if key_prefix in content:
                            os.remove(fpath)
                    except Exception:
                        pass

    def make_key(self, *parts: str) -> str:
        raw = ":".join(str(p) for p in parts if p)
        return hashlib.sha256(raw.encode()).hexdigest()

    def clear(self) -> None:
        self._memory_cache.clear()
        self._invalidated.clear()
        self._hits = 0
        self._misses = 0

    def stats(self) -> dict:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": round(self._hits / (self._hits + self._misses), 3) if (self._hits + self._misses) > 0 else 0,
            "memory_entries": len(self._memory_cache),
        }

    def _key_to_path(self, key: str) -> str:
        hashed = self._hash_key(key)
        return os.path.join(self._cache_dir, f"{hashed}.json")

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()[:32]
