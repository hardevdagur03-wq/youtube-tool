"""Transaction Logger — immutable event log for pipeline execution.

Every pipeline event is logged as an immutable entry with full context:
timestamp, execution_id, stage, action, correlation_id, trace_id, etc.
All entries are append-only and never modified.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from production_pipeline.config import PipelineHardeningConfig
from production_pipeline.exceptions import TransactionLogError
from production_pipeline.models import ExecutionEvent

logger = logging.getLogger(__name__)


class TransactionLogger:
    """Immutable transaction log for pipeline execution events.

    Every event is logged with full context including correlation and trace IDs
    for distributed tracing. Events are append-only — never modified or deleted.
    """

    def __init__(self, config: PipelineHardeningConfig | None = None) -> None:
        self._config = config or PipelineHardeningConfig()
        self._events: list[ExecutionEvent] = []

    def log_event(
        self,
        execution_id: str,
        action: str,
        stage_name: str = "",
        status: str = "",
        request_id: str = "",
        correlation_id: str = "",
        trace_id: str = "",
        worker_id: str = "",
        duration_ms: float = 0.0,
        retry_count: int = 0,
        error: str = "",
        details: dict[str, Any] | None = None,
    ) -> ExecutionEvent:
        """Log an immutable execution event.

        Args:
            execution_id: Workflow execution ID.
            action: Action type (e.g. 'stage_started', 'checkpoint_saved').
            stage_name: Stage name (if applicable).
            status: Status of the action.
            request_id: HTTP request ID.
            correlation_id: Correlation ID for distributed tracing.
            trace_id: OpenTelemetry trace ID.
            worker_id: Worker that processed the event.
            duration_ms: Duration in milliseconds.
            retry_count: Retry count at time of event.
            error: Error message (if any).
            details: Additional event details.

        Returns:
            ``ExecutionEvent`` that was logged.
        """
        event = ExecutionEvent(
            event_id=str(uuid.uuid4()),
            execution_id=execution_id,
            stage_name=stage_name,
            action=action,
            status=status,
            request_id=request_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
            worker_id=worker_id,
            duration_ms=duration_ms,
            retry_count=retry_count,
            error=error,
            details=details or {},
        )

        self._events.append(event)

        logger.debug(
            "Transaction logged: execution=%s action=%s stage=%s status=%s",
            execution_id[:8], action, stage_name, status,
        )

        return event

    def get_events(
        self, execution_id: str, limit: int = 100
    ) -> list[ExecutionEvent]:
        """Get all events for an execution.

        Args:
            execution_id: Workflow execution ID.
            limit: Maximum number of events to return.

        Returns:
            List of ``ExecutionEvent`` in chronological order.
        """
        events = [e for e in self._events if e.execution_id == execution_id]
        return events[-limit:]

    def get_events_by_correlation(
        self, correlation_id: str, limit: int = 100
    ) -> list[ExecutionEvent]:
        """Get events by correlation ID for distributed tracing.

        Args:
            correlation_id: Correlation ID.
            limit: Maximum number of events.

        Returns:
            List of ``ExecutionEvent``.
        """
        events = [e for e in self._events if e.correlation_id == correlation_id]
        return events[-limit:]

    def get_events_by_action(
        self, action: str, limit: int = 100
    ) -> list[ExecutionEvent]:
        """Get events by action type.

        Args:
            action: Action type filter.
            limit: Maximum number of events.

        Returns:
            List of ``ExecutionEvent``.
        """
        events = [e for e in self._events if e.action == action]
        return events[-limit:]

    def get_all_events(self, limit: int = 1000) -> list[ExecutionEvent]:
        """Get all logged events.

        Args:
            limit: Maximum number of events.

        Returns:
            List of ``ExecutionEvent``.
        """
        return self._events[-limit:]

    def get_event_count(self, execution_id: str | None = None) -> int:
        """Get event count, optionally filtered by execution.

        Args:
            execution_id: Optional execution filter.

        Returns:
            Number of events.
        """
        if execution_id:
            return len([e for e in self._events if e.execution_id == execution_id])
        return len(self._events)

    def get_timeline(self, execution_id: str) -> list[dict[str, Any]]:
        """Get a simplified timeline of events for an execution.

        Args:
            execution_id: Workflow execution ID.

        Returns:
            List of event summaries in chronological order.
        """
        events = self.get_events(execution_id)
        return [
            {
                "timestamp": e.timestamp,
                "action": e.action,
                "stage": e.stage_name,
                "status": e.status,
                "duration_ms": e.duration_ms,
                "error": e.error,
            }
            for e in events
        ]

    def clear(self) -> None:
        """Clear all logged events."""
        self._events.clear()
