"""Dead Letter Queue — stores permanently failed jobs for manual inspection and replay."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Sequence

from redis.asyncio import Redis

from background_processing.config import BackgroundProcessingConfig
from background_processing.models import DeadLetterEntry, JobModel, RetryAttempt
from background_processing.retry_manager import RetryManager

logger = logging.getLogger(__name__)


# Recovery recommendation rules
RECOVERY_RULES: dict[str, str] = {
    "TimeoutError": "Increase task timeout or reduce payload size.",
    "ConnectionError": "Check Redis/broker connectivity and restart workers.",
    "DatabaseError": "Check database connectivity and connection pool.",
    "APIError": "Check external API key, rate limits, and quotas.",
    "OpenAIError": "Check OpenAI API key, quota, and model availability.",
    "YouTubeError": "Check YouTube API key and quota.",
    "SerializationError": "Payload may contain non-serializable types. Check job payload.",
    "MemoryError": "Worker ran out of memory. Increase worker_max_memory_per_child.",
}


class DeadLetterQueue:
    """Manages the Dead Letter Queue for permanently failed jobs.

    Jobs that exceed their maximum retry count or hit non-recoverable
    errors are moved here. They can be inspected, replayed, or purged.
    """

    def __init__(
        self,
        redis_client: Redis | None = None,
        config: BackgroundProcessingConfig | None = None,
        retry_manager: RetryManager | None = None,
    ) -> None:
        self._config = config or BackgroundProcessingConfig.from_env()
        self._redis = redis_client
        self._retry_mgr = retry_manager or RetryManager(config)

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(
                self._config.redis_url,
                decode_responses=True,
            )
        return self._redis

    async def send(
        self,
        job: JobModel,
        error: str = "",
        traceback: str = "",
    ) -> DeadLetterEntry:
        """Move a failed job to the dead letter queue."""
        redis = await self._get_redis()
        dlq_key = f"dlq:{job.uuid}"

        entry = DeadLetterEntry(
            job_id=job.uuid,
            project_id=job.project_id or "",
            job_type=job.job_type,
            payload=job.payload or {},
            error=error[:2000] if error else "",
            traceback=traceback[:5000] if traceback else "",
            retry_history=[RetryAttempt(**a) for a in (job.retry_history or [])],
            failed_at=datetime.now(timezone.utc).isoformat(),
            recovery_recommendation=self._recommend_recovery(error),
        )

        await redis.set(dlq_key, entry.model_dump_json(), ex=604800)  # 7 day TTL

        dlq_list_key = "dlq:jobs"
        await redis.lpush(dlq_list_key, job.uuid)
        await redis.ltrim(dlq_list_key, 0, 9999)

        logger.warning(
            "Job sent to DLQ: %s [%s] — %s",
            job.uuid[:8], job.job_type, error[:100],
        )
        return entry

    async def get(self, job_id: str) -> DeadLetterEntry | None:
        """Retrieve a dead letter entry for inspection."""
        redis = await self._get_redis()
        data = await redis.get(f"dlq:{job_id}")
        if data is None:
            return None
        try:
            parsed = json.loads(data) if isinstance(data, str) else data
            return DeadLetterEntry(**parsed)
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("Failed to parse DLQ entry %s: %s", job_id, exc)
            return None

    async def list(
        self, limit: int = 100, offset: int = 0
    ) -> list[DeadLetterEntry]:
        """List dead letter entries (newest first)."""
        redis = await self._get_redis()
        dlq_list_key = "dlq:jobs"
        job_ids = await redis.lrange(dlq_list_key, offset, offset + limit - 1)
        entries = []
        for jid in job_ids:
            entry = await self.get(jid)
            if entry:
                entries.append(entry)
        return entries

    async def count(self) -> int:
        """Get the number of entries in the DLQ."""
        redis = await self._get_redis()
        return await redis.llen("dlq:jobs")

    async def replay(self, job_id: str, job_repo: Any) -> JobModel | None:
        """Replay a dead letter job by resetting its status to pending.

        Returns the updated JobModel if successful.
        """
        entry = await self.get(job_id)
        if entry is None:
            logger.warning("DLQ replay failed: entry not found %s", job_id[:8])
            return None

        job = await job_repo.get(job_id)
        if job is None:
            logger.warning("DLQ replay failed: job not found %s", job_id[:8])
            return None

        job = await job_repo.update(
            job_id,
            status="pending",
            attempts=0,
            error="",
            traceback="",
            recoverable=True,
        )

        # Remove from DLQ
        redis = await self._get_redis()
        await redis.delete(f"dlq:{job_id}")
        await redis.lrem("dlq:jobs", 1, job_id)

        logger.info("DLQ replay: job %s returned to queue", job_id[:8])
        return job

    async def replay_all(self, job_repo: Any) -> int:
        """Replay all dead letter jobs."""
        entries = await self.list(limit=1000)
        count = 0
        for entry in entries:
            result = await self.replay(entry.job_id, job_repo)
            if result:
                count += 1
        return count

    async def purge(self, job_id: str) -> bool:
        """Remove a job from the dead letter queue permanently."""
        redis = await self._get_redis()
        await redis.delete(f"dlq:{job_id}")
        await redis.lrem("dlq:jobs", 1, job_id)
        logger.info("DLQ purged: %s", job_id[:8])
        return True

    async def purge_all(self) -> int:
        """Remove all jobs from the dead letter queue."""
        redis = await self._get_redis()
        count = await redis.llen("dlq:jobs")
        dlq_keys = await redis.keys("dlq:*")
        if dlq_keys:
            await redis.delete(*dlq_keys)
        logger.info("DLQ purged all: %d entries", count)
        return count

    def _recommend_recovery(self, error: str) -> str:
        """Generate a recovery recommendation based on the error message."""
        for error_type, recommendation in RECOVERY_RULES.items():
            if error_type in error:
                return recommendation
        return "Check worker logs and infrastructure health."
