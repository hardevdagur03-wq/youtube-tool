from __future__ import annotations

import hashlib
import json
import time
from typing import Any


class PromptCacheEntry:
    __slots__ = ("value", "expires_at", "created_at")

    def __init__(self, value: str, ttl: float):
        self.value = value
        self.created_at = time.time()
        self.expires_at = time.time() + ttl

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def age(self) -> float:
        return time.time() - self.created_at


class PromptCache:
    def __init__(self, default_ttl: float = 300.0, max_size: int = 1000):
        self._store: dict[str, PromptCacheEntry] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        if entry.is_expired():
            del self._store[key]
            self._misses += 1
            return None
        self._hits += 1
        return entry.value

    def set(self, key: str, value: str, ttl: float | None = None) -> None:
        if len(self._store) >= self._max_size:
            self._evict()
        self._store[key] = PromptCacheEntry(value, ttl or self._default_ttl)

    def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def clear(self) -> None:
        self._store.clear()
        self._hits = 0
        self._misses = 0

    def invalidate_pattern(self, pattern: str) -> int:
        import re
        pat = re.compile(pattern.replace("*", ".*"))
        keys = [k for k in self._store if pat.match(k)]
        for k in keys:
            del self._store[k]
        return len(keys)

    def get_or_set(self, key: str, factory: Any, ttl: float | None = None) -> str:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = factory() if callable(factory) else str(factory)
        self.set(key, value, ttl)
        return value

    def stats(self) -> dict[str, Any]:
        total = self._hits + self._misses
        return {
            "size": len(self._store),
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": self._hits / total if total > 0 else 0.0,
            "max_size": self._max_size,
            "default_ttl": self._default_ttl,
        }

    def make_key(self, namespace: str, identifier: str) -> str:
        raw = f"prompt:{namespace}:{identifier}"
        if len(raw) > 120:
            return f"prompt:{namespace}:{hashlib.sha256(raw.encode()).hexdigest()[:32]}"
        return raw

    def _evict(self) -> None:
        if not self._store:
            return
        oldest = min(self._store.items(), key=lambda x: x[1].created_at)
        del self._store[oldest[0]]

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: str) -> bool:
        entry = self._store.get(key)
        if entry is None or entry.is_expired():
            return False
        return True
