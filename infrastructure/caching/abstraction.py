"""Cache abstraction interface.

Domain depends on this interface.
Infrastructure provides implementations (memory, Redis, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CacheBackend(ABC):
    """Abstract cache backend interface."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    async def clear(self) -> None:
        ...

    @abstractmethod
    async def get_or_set(
        self, key: str, factory: Any, ttl: int = 300
    ) -> Any:
        ...


class InMemoryCache(CacheBackend):
    """Thread-safe in-memory cache implementation."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._ttls: dict[str, float] = {}

    async def get(self, key: str) -> Any | None:
        if key in self._ttls:
            import time
            if time.time() > self._ttls[key]:
                self._store.pop(key, None)
                self._ttls.pop(key, None)
                return None
        return self._store.get(key)

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        import time
        self._store[key] = value
        if ttl > 0:
            self._ttls[key] = time.time() + ttl

    async def delete(self, key: str) -> bool:
        existed = key in self._store
        self._store.pop(key, None)
        self._ttls.pop(key, None)
        return existed

    async def exists(self, key: str) -> bool:
        if key in self._ttls:
            import time
            if time.time() > self._ttls[key]:
                self._store.pop(key, None)
                self._ttls.pop(key, None)
                return False
        return key in self._store

    async def clear(self) -> None:
        self._store.clear()
        self._ttls.clear()

    async def get_or_set(self, key: str, factory: Any, ttl: int = 300) -> Any:
        existing = await self.get(key)
        if existing is not None:
            return existing
        value = await factory() if callable(factory) else factory
        await self.set(key, value, ttl)
        return value


class CacheService:
    """High-level cache service wrapping a backend.

    Provides namespacing and serialization.
    """

    def __init__(self, backend: CacheBackend | None = None) -> None:
        self._backend = backend or InMemoryCache()
        self._hits = 0
        self._misses = 0

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": round(self._hits / total * 100, 1) if total > 0 else 0,
        }

    async def get(self, namespace: str, key: str) -> Any | None:
        full_key = f"{namespace}:{key}"
        value = await self._backend.get(full_key)
        if value is not None:
            self._hits += 1
        else:
            self._misses += 1
        return value

    async def set(self, namespace: str, key: str, value: Any, ttl: int = 300) -> None:
        full_key = f"{namespace}:{key}"
        await self._backend.set(full_key, value, ttl)

    async def delete(self, namespace: str, key: str) -> bool:
        full_key = f"{namespace}:{key}"
        return await self._backend.delete(full_key)

    async def clear_namespace(self, namespace: str) -> None:
        if isinstance(self._backend, InMemoryCache):
            prefix = f"{namespace}:"
            keys = [k for k in self._backend._store if k.startswith(prefix)]
            for k in keys:
                await self._backend.delete(k)

    async def get_or_set(
        self, namespace: str, key: str, factory: Any, ttl: int = 300
    ) -> Any:
        full_key = f"{namespace}:{key}"
        value = await self._backend.get(full_key)
        if value is not None:
            self._hits += 1
            return value
        self._misses += 1
        value = await factory() if callable(factory) else factory
        await self._backend.set(full_key, value, ttl)
        return value
