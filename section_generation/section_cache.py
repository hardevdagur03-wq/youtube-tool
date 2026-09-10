"""Section Cache — per-section independent caching.

Each section has its own cache entry with prompt hash, response,
metadata, version, validation result, and checksum.
Supports cache hit, miss, refresh, and version validation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from typing import Any

from section_generation.section_models import (
    SectionType,
    SectionOutput,
    SectionContext,
    utc_now,
)

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS: dict[SectionType, float] = {
    SectionType.INTRODUCTION: 86400,
    SectionType.PROBLEM: 86400,
    SectionType.EXPLANATION: 86400,
    SectionType.STEP_BY_STEP: 86400,
    SectionType.COMPARISON: 86400,
    SectionType.DEFINITION: 86400,
    SectionType.BENEFITS: 86400,
    SectionType.DRAWBACKS: 86400,
    SectionType.USE_CASES: 86400,
    SectionType.EXAMPLES: 86400,
    SectionType.CASE_STUDIES: 86400,
    SectionType.TABLE: 86400,
    SectionType.LIST: 86400,
    SectionType.CODE: 86400,
    SectionType.QUOTE: 86400,
    SectionType.FAQ: 3600,
    SectionType.SUMMARY: 3600,
    SectionType.CONCLUSION: 3600,
    SectionType.CTA: 3600,
    SectionType.BODY: 86400,
}


class CacheEntry:
    __slots__ = ("prompt_hash", "response", "metadata", "version",
                 "validation", "checksum", "created_at", "expires_at",
                 "hit_count", "section_id")

    def __init__(
        self,
        prompt_hash: str,
        response: str,
        metadata: dict[str, Any] | None = None,
        version: int = 1,
        validation: dict[str, Any] | None = None,
        ttl_seconds: float = 86400,
        section_id: str = "",
    ) -> None:
        self.prompt_hash = prompt_hash
        self.response = response
        self.metadata = metadata or {}
        self.version = version
        self.validation = validation or {}
        self.checksum = hashlib.sha256(response.encode()).hexdigest()[:16]
        self.created_at = time.time()
        self.expires_at = time.time() + ttl_seconds
        self.hit_count = 0
        self.section_id = section_id

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def is_valid_version(self, expected_version: int) -> bool:
        return self.version >= expected_version

    def verify_checksum(self) -> bool:
        current = hashlib.sha256(self.response.encode()).hexdigest()[:16]
        return current == self.checksum


class SectionCache:
    """Per-section cache with prompt hashing and version validation."""

    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(
        self,
        section_type: SectionType,
        context: SectionContext,
    ) -> str:
        stable = json.dumps({
            "type": section_type.value,
            "heading": context.heading,
            "goal": context.goal,
            "keywords": sorted(context.keywords),
            "entities": sorted(context.entities),
            "primary_keyword": context.primary_keyword,
            "target_audience": context.target_audience,
            "search_intent": context.search_intent,
            "tone": context.tone,
            "word_count": context.target_word_count,
        }, sort_keys=True, default=str)
        return hashlib.sha256(stable.encode()).hexdigest()[:32]

    def get(
        self,
        section_type: SectionType,
        context: SectionContext,
        expected_version: int = 1,
    ) -> SectionOutput | None:
        key = self._make_key(section_type, context)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired():
                del self._store[key]
                self._misses += 1
                return None
            if not entry.is_valid_version(expected_version):
                logger.debug("Cache version mismatch for %s", key[:12])
                self._misses += 1
                return None
            if not entry.verify_checksum():
                logger.warning("Cache checksum mismatch for %s", key[:12])
                del self._store[key]
                self._misses += 1
                return None

            entry.hit_count += 1
            self._hits += 1
            logger.debug("Cache HIT for section %s (key=%s)", section_type.value, key[:12])

            return SectionOutput(
                section_id=entry.section_id or key[:12],
                section_type=section_type,
                content=entry.response,
                version=entry.version,
                cache_hit=True,
                status="completed",
            )

    def set(
        self,
        section_type: SectionType,
        context: SectionContext,
        output: SectionOutput,
    ) -> None:
        key = self._make_key(section_type, context)
        ttl = CACHE_TTL_SECONDS.get(section_type, 86400)
        with self._lock:
            self._store[key] = CacheEntry(
                prompt_hash=key,
                response=output.content,
                metadata={
                    "section_id": output.section_id,
                    "section_type": section_type.value,
                    "word_count": output.word_count,
                    "version": output.version,
                },
                version=output.version,
                ttl_seconds=ttl,
                section_id=output.section_id,
            )
            logger.debug("Cache SET for section %s (key=%s)", section_type.value, key[:12])

    def invalidate(
        self,
        section_type: SectionType,
        context: SectionContext,
    ) -> None:
        key = self._make_key(section_type, context)
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> dict[str, Any]:
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": round(self._hits / total * 100, 1) if total > 0 else 0,
            "size": len(self._store),
        }
