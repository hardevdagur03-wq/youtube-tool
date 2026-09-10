"""Dead Letter Queue — pipeline-level DLQ for failed workflows.

Integrates with the existing background_processing/dead_letter_queue.py.
Failed pipeline stages move to the DLQ with full payload, error context,
and retry history. Supports replay, bulk retry, and export for diagnostics.
"""

from __future__ import annotations

import logging
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any

from production_pipeline.config import PipelineHardeningConfig
from production_pipeline.constants import ErrorClass
from production_pipeline.error_handler import classify_error
from production_pipeline.exceptions import DeadLetterError
from production_pipeline.models import DeadLetterRecord

logger = logging.getLogger(__name__)


class PipelineDeadLetterQueue:
    """Pipeline-level dead letter queue for failed workflow stages.

    Stores failed stage executions with full context: error details,
    payload, retry history, and recovery metadata.
    Supports manual and automated replay.
    """

    def __init__(self, config: PipelineHardeningConfig | None = None) -> None:
        self._config = config or PipelineHardeningConfig()
        self._entries: dict[str, DeadLetterRecord] = {}

    def send(
        self,
        execution_id: str,
        project_id: str,
        stage_name: str,
        error: Exception | str,
        payload: dict[str, Any] | None = None,
        retry_count: int = 0,
        retry_history: list[dict[str, Any]] | None = None,
    ) -> DeadLetterRecord:
        """Send a failed stage to the dead letter queue.

        Args:
            execution_id: Workflow execution ID.
            project_id: Project ID.
            stage_name: Stage that failed.
            error: The exception or error string.
            payload: Stage input payload.
            retry_count: Number of retries attempted.
            retry_history: History of retry attempts.

        Returns:
            ``DeadLetterRecord`` that was created.
        """
        error_str = str(error)
        tb = ""
        if isinstance(error, Exception):
            tb = traceback.format_exc()

        error_class, _, _ = classify_error(error)

        dlq_id = str(uuid.uuid4())
        record = DeadLetterRecord(
            dlq_id=dlq_id,
            execution_id=execution_id,
            project_id=project_id,
            stage_name=stage_name,
            error=error_str,
            error_class=error_class.value,
            traceback=tb[:2000],
            payload=payload or {},
            retry_count=retry_count,
            retry_history=retry_history or [],
            recovery_status="pending",
        )

        self._entries[dlq_id] = record

        logger.warning(
            "DLQ entry created: execution=%s stage=%s error=%s (dlq_id=%s)",
            execution_id[:8], stage_name, error_class.value, dlq_id[:8],
        )

        return record

    def get(self, dlq_id: str) -> DeadLetterRecord | None:
        """Get a DLQ entry by ID.

        Args:
            dlq_id: DLQ entry ID.

        Returns:
            ``DeadLetterRecord`` if found, else None.
        """
        return self._entries.get(dlq_id)

    def list(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[DeadLetterRecord]:
        """List DLQ entries, optionally filtered by status.

        Args:
            status: Filter by recovery status ('pending', 'recovered', 'failed').
            limit: Maximum number of entries.

        Returns:
            List of ``DeadLetterRecord``.
        """
        entries = list(self._entries.values())
        if status:
            entries = [e for e in entries if e.recovery_status == status]
        return entries[:limit]

    def count(self, status: str | None = None) -> int:
        """Count DLQ entries.

        Args:
            status: Optional status filter.

        Returns:
            Number of matching entries.
        """
        if status:
            return sum(1 for e in self._entries.values() if e.recovery_status == status)
        return len(self._entries)

    def replay(self, dlq_id: str) -> bool:
        """Mark a DLQ entry for replay (sets status to 'pending' for retry).

        Args:
            dlq_id: DLQ entry ID.

        Returns:
            True if the entry was marked for replay.
        """
        record = self._entries.get(dlq_id)
        if record is None:
            return False
        record.recovery_status = "pending"
        record.retry_count = 0
        logger.info("DLQ entry marked for replay: %s", dlq_id[:8])
        return True

    def replay_all(self, status: str = "pending") -> int:
        """Mark all DLQ entries for replay.

        Args:
            status: Filter entries by current status.

        Returns:
            Number of entries marked for replay.
        """
        count = 0
        for record in self._entries.values():
            if record.recovery_status == status:
                record.recovery_status = "pending"
                record.retry_count = 0
                count += 1
        logger.info("DLQ: %d entries marked for replay", count)
        return count

    def mark_recovered(self, dlq_id: str) -> bool:
        """Mark a DLQ entry as recovered.

        Args:
            dlq_id: DLQ entry ID.

        Returns:
            True if the entry was marked recovered.
        """
        record = self._entries.get(dlq_id)
        if record is None:
            return False
        record.recovery_status = "recovered"
        record.recovered_at = datetime.now(timezone.utc).isoformat()
        return True

    def mark_failed(self, dlq_id: str) -> bool:
        """Mark a DLQ entry as permanently failed.

        Args:
            dlq_id: DLQ entry ID.

        Returns:
            True if the entry was marked failed.
        """
        record = self._entries.get(dlq_id)
        if record is None:
            return False
        record.recovery_status = "failed"
        return True

    def purge(self, status: str | None = None) -> int:
        """Purge DLQ entries.

        Args:
            status: Optional status filter.

        Returns:
            Number of purged entries.
        """
        if status:
            to_purge = [k for k, v in self._entries.items() if v.recovery_status == status]
            for k in to_purge:
                del self._entries[k]
            return len(to_purge)
        count = len(self._entries)
        self._entries.clear()
        return count

    def export(self, limit: int = 100) -> list[dict[str, Any]]:
        """Export DLQ entries for diagnostics.

        Args:
            limit: Maximum number of entries.

        Returns:
            List of serialized DLQ entries.
        """
        return [
            {
                "dlq_id": e.dlq_id,
                "execution_id": e.execution_id[:8],
                "project_id": e.project_id,
                "stage_name": e.stage_name,
                "error": e.error[:200],
                "error_class": e.error_class,
                "retry_count": e.retry_count,
                "recovery_status": e.recovery_status,
                "created_at": e.created_at,
            }
            for e in list(self._entries.values())[:limit]
        ]
