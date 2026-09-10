"""Rate Limiter — token bucket rate limiting for job dispatch.

Prevents any single tenant, user, or project from overwhelming the system.
Uses Redis for distributed rate limiting across all workers and API servers.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from redis.asyncio import Redis

from background_processing.config import BackgroundProcessingConfig

logger = logging.getLogger(__name__)

# Rate limit configurations per scope
DEFAULT_LIMITS = {
    "tenant": {"max_burst": 100, "per_second": 10},
    "user": {"max_burst": 50, "per_second": 5},
    "project": {"max_burst": 20, "per_second": 2},
    "global": {"max_burst": 500, "per_second": 50},
}

TOKEN_BUCKET_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local max_burst = tonumber(ARGV[2])
local fill_rate = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])

local bucket = redis.call("HMGET", key, "tokens", "last_refill")
local tokens = tonumber(bucket[1]) or max_burst
local last_refill = tonumber(bucket[2]) or now

local elapsed = math.max(0, now - last_refill)
tokens = math.min(max_burst, tokens + elapsed * fill_rate)
last_refill = now

if tokens >= cost then
    tokens = tokens - cost
    redis.call("HMSET", key, "tokens", tokens, "last_refill", last_refill)
    redis.call("EXPIRE", key, 60)
    return 1
else
    redis.call("HMSET", key, "tokens", tokens, "last_refill", last_refill)
    redis.call("EXPIRE", key, 60)
    return 0
end
"""


class RateLimitExceeded(Exception):
    """Raised when a rate limit is exceeded."""


class RateLimiter:
    """Distributed rate limiter using Redis token bucket algorithm.

    Supports multiple scopes:
    - Global: across the entire platform
    - Tenant: per organization
    - User: per authenticated user
    - Project: per project
    - Type: per job type
    """

    def __init__(
        self,
        redis_client: Redis | None = None,
        config: BackgroundProcessingConfig | None = None,
        limits: dict[str, dict[str, int]] | None = None,
    ) -> None:
        self._redis = redis_client
        self._config = config or BackgroundProcessingConfig.from_env()
        self._limits = {**DEFAULT_LIMITS, **(limits or {})}

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(
                self._config.redis_url,
                decode_responses=True,
                socket_timeout=5,
            )
        return self._redis

    async def allow(
        self,
        tenant_id: str = "",
        user_id: str = "",
        job_type: str = "",
        cost: int = 1,
    ) -> bool:
        """Check if a request should be allowed based on all applicable rate limits.

        Args:
            tenant_id: Tenant/organization identifier.
            user_id: User identifier.
            job_type: Type of job being created.
            cost: Cost of this operation (default 1).

        Returns:
            True if allowed, False if rate limited.

        Note: If Redis is unavailable, rate limiting is bypassed (fail-open)
        to ensure the platform remains operational during Redis outages.
        """
        try:
            redis = await self._get_redis()
        except Exception as exc:
            logger.warning("Rate limiter unavailable (Redis down?), allowing: %s", exc)
            return True

        now = int(time.time())

        checks = [
            ("global", "global", self._limits.get("global", DEFAULT_LIMITS["global"])),
        ]
        if tenant_id:
            checks.append(("tenant", f"tenant:{tenant_id}", self._limits.get("tenant", DEFAULT_LIMITS["tenant"])))
        if user_id:
            checks.append(("user", f"user:{user_id}", self._limits.get("user", DEFAULT_LIMITS["user"])))
        if job_type:
            checks.append(("type", f"type:{job_type}", self._limits.get("type", {"max_burst": 30, "per_second": 3})))

        for scope_name, scope_key, limit_cfg in checks:
            try:
                redis_key = f"ratelimit:{scope_key}"
                allowed = await redis.eval(
                    TOKEN_BUCKET_SCRIPT,
                    1, redis_key, str(now),
                    str(limit_cfg["max_burst"]),
                    str(limit_cfg["per_second"]),
                    str(cost),
                )
                if not allowed:
                    logger.warning("Rate limit exceeded: scope=%s key=%s", scope_name, scope_key)
                    return False
            except Exception as exc:
                logger.warning("Rate limit check failed for scope %s: %s", scope_name, exc)
                continue

        return True

    async def remaining(self, tenant_id: str = "", user_id: str = "") -> dict[str, int]:
        """Get remaining tokens for all applicable scopes."""
        redis = await self._get_redis()
        now = int(time.time())
        result: dict[str, int] = {}

        scopes = [("global", "global")]
        if tenant_id:
            scopes.append(("tenant", f"tenant:{tenant_id}"))
        if user_id:
            scopes.append(("user", f"user:{user_id}"))

        for scope_name, scope_key in scopes:
            redis_key = f"ratelimit:{scope_key}"
            bucket = await redis.hmget(redis_key, "tokens", "last_refill")
            tokens = float(bucket[0]) if bucket[0] else None
            last_refill = float(bucket[1]) if bucket[1] else now
            if tokens is not None:
                limit_cfg = self._limits.get(scope_name, DEFAULT_LIMITS.get(scope_name, {"max_burst": 50, "per_second": 5}))
                elapsed = max(0, now - last_refill)
                tokens = min(limit_cfg["max_burst"], tokens + elapsed * limit_cfg["per_second"])
                result[scope_name] = int(tokens)
            else:
                result[scope_name] = -1

        return result

    async def reset(self, tenant_id: str = "", user_id: str = "") -> None:
        """Reset rate limits for a given scope."""
        redis = await self._get_redis()
        keys = ["ratelimit:global"]
        if tenant_id:
            keys.append(f"ratelimit:tenant:{tenant_id}")
        if user_id:
            keys.append(f"ratelimit:user:{user_id}")
        if keys:
            await redis.delete(*keys)
