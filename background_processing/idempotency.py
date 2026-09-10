"""Idempotency Engine — prevents duplicate job execution via unique job keys.

Every job carries an idempotency key derived from (tenant, project, type, payload).
Duplicate detection happens before dispatch.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis

from background_processing.config import BackgroundProcessingConfig

logger = logging.getLogger(__name__)


@dataclass
class DedupResult:
    is_duplicate: bool
    existing_job_id: str = ""
    existing_status: str = ""


class IdempotencyEngine:
    """Ensures each unique job is only created once within a TTL window.

    Key format: idempotent:<key_hash>:<project_id>:<job_type>
    Values are JSON with job_id, status, and timestamp.
    """

    def __init__(
        self,
        redis_client: Redis | None = None,
        config: BackgroundProcessingConfig | None = None,
    ) -> None:
        self._redis = redis_client
        self._config = config or BackgroundProcessingConfig.from_env()

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(
                self._config.redis_url,
                decode_responses=True,
                socket_timeout=5,
            )
        return self._redis

    async def check(self, job_key: str) -> DedupResult:
        """Check if a job with this key has already been submitted.

        Gracefully handles Redis failures by returning non-duplicate,
        allowing the job to proceed. This is safe because idempotency
        is a best-effort optimization, not a correctness guarantee.
        """
        try:
            redis = await self._get_redis()
            redis_key = f"idempotent:{self._hash_key(job_key)}"
            existing = await redis.get(redis_key)
            if existing:
                try:
                    data = json.loads(existing)
                    return DedupResult(
                        is_duplicate=True,
                        existing_job_id=data.get("job_id", ""),
                        existing_status=data.get("status", ""),
                    )
                except (json.JSONDecodeError, TypeError):
                    pass
        except Exception as exc:
            logger.warning("Idempotency check failed (Redis may be down): %s", exc)
        return DedupResult(is_duplicate=False)

    async def record(self, job_key: str, job_id: str, ttl: int = 86400) -> None:
        """Record a job's idempotency key to prevent future duplicates."""
        try:
            redis = await self._get_redis()
            redis_key = f"idempotent:{self._hash_key(job_key)}"
            data = json.dumps({"job_id": job_id, "status": "queued", "timestamp": time.time()})
            await redis.set(redis_key, data, ex=ttl)
            logger.debug("Idempotency recorded: key=%s job=%s ttl=%ds", redis_key[:24], job_id[:8], ttl)
        except Exception as exc:
            logger.warning("Idempotency record failed: %s", exc)

    async def release(self, job_key: str) -> None:
        """Remove an idempotency key (for re-dispatch)."""
        try:
            redis = await self._get_redis()
            redis_key = f"idempotent:{self._hash_key(job_key)}"
            await redis.delete(redis_key)
        except Exception as exc:
            logger.warning("Idempotency release failed: %s", exc)

    async def update_status(self, job_key: str, status: str) -> None:
        """Update the status on an existing idempotency record."""
        try:
            redis = await self._get_redis()
            redis_key = f"idempotent:{self._hash_key(job_key)}"
            existing = await redis.get(redis_key)
            if existing:
                try:
                    data = json.loads(existing)
                    data["status"] = status
                    await redis.set(redis_key, json.dumps(data), keepttl=True)
                except (json.JSONDecodeError, TypeError):
                    pass
        except Exception as exc:
            logger.warning("Idempotency update_status failed: %s", exc)

    def _hash_key(self, key: str) -> str:
        import hashlib
        return hashlib.sha256(key.encode()).hexdigest()[:32]
