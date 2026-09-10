"""Execution History — full execution timeline and history service.

Builds complete execution timelines from transaction logs.
Supports timeline queries, diffs between runs, and history filtering.
"""

from __future__ import annotations

import logging
from typing import Any

from production_pipeline.models import ExecutionEvent
from production_pipeline.transaction_logger import TransactionLogger

logger = logging.getLogger(__name__)


class ExecutionHistory:
    """Full execution timeline and history service.

    Builds timelines from transaction log events and provides
    query, diff, and filtering capabilities.
    """

    def __init__(self, logger: TransactionLogger) -> None:
        self._logger = logger

    def get_timeline(self, execution_id: str) -> list[dict[str, Any]]:
        """Get the full execution timeline.

        Args:
            execution_id: Workflow execution ID.

        Returns:
            Chronological list of timeline entries.
        """
        return self._logger.get_timeline(execution_id)

    def get_stage_timeline(
        self, execution_id: str, stage_name: str
    ) -> list[dict[str, Any]]:
        """Get the timeline for a specific stage.

        Args:
            execution_id: Workflow execution ID.
            stage_name: Stage name.

        Returns:
            Chronological list of events for the stage.
        """
        events = self._logger.get_events(execution_id)
        stage_events = [e for e in events if e.stage_name == stage_name]
        return [
            {
                "timestamp": e.timestamp,
                "action": e.action,
                "status": e.status,
                "duration_ms": e.duration_ms,
                "error": e.error,
            }
            for e in stage_events
        ]

    def get_latest_executions(
        self, project_id: str, limit: int = 10
    ) -> list[str]:
        """Get the latest execution IDs for a project.

        Args:
            project_id: Project ID.
            limit: Maximum number of executions.

        Returns:
            List of execution IDs, most recent first.
        """
        all_events = self._logger.get_all_events(limit=1000)
        execution_ids = set()
        for event in all_events:
            execution_ids.add(event.execution_id)
        return list(execution_ids)[:limit]

    def compare_executions(
        self, execution_id_a: str, execution_id_b: str
    ) -> dict[str, Any]:
        """Compare two pipeline executions.

        Args:
            execution_id_a: First execution ID.
            execution_id_b: Second execution ID.

        Returns:
            Dict with comparison data.
        """
        timeline_a = self.get_timeline(execution_id_a)
        timeline_b = self.get_timeline(execution_id_b)

        stages_a = {e["stage"] for e in timeline_a if e.get("stage")}
        stages_b = {e["stage"] for e in timeline_b if e.get("stage")}

        a_only = stages_a - stages_b
        b_only = stages_b - stages_a
        common = stages_a & stages_b

        return {
            "execution_a": execution_id_a,
            "execution_b": execution_id_b,
            "stages_only_in_a": list(a_only),
            "stages_only_in_b": list(b_only),
            "common_stages": list(common),
            "total_events_a": len(timeline_a),
            "total_events_b": len(timeline_b),
        }

    def get_summary(self, execution_id: str) -> dict[str, Any]:
        """Get a summary of the execution.

        Args:
            execution_id: Workflow execution ID.

        Returns:
            Summary dict with key metrics.
        """
        events = self._logger.get_events(execution_id)
        if not events:
            return {"execution_id": execution_id, "events": 0}

        total_duration = sum(e.duration_ms for e in events)
        stage_events = [e for e in events if e.stage_name]
        unique_stages = set(e.stage_name for e in stage_events)
        errors = [e for e in events if e.error]
        retries = sum(e.retry_count for e in events)

        return {
            "execution_id": execution_id,
            "total_events": len(events),
            "unique_stages": len(unique_stages),
            "total_duration_ms": round(total_duration, 1),
            "error_count": len(errors),
            "total_retries": retries,
            "first_event": events[0].timestamp if events else "",
            "last_event": events[-1].timestamp if events else "",
        }

    def query(
        self,
        execution_id: str | None = None,
        action: str | None = None,
        stage_name: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query execution events with filters.

        Args:
            execution_id: Optional execution filter.
            action: Optional action filter.
            stage_name: Optional stage filter.
            status: Optional status filter.
            limit: Maximum results.

        Returns:
            Filtered list of event summaries.
        """
        if execution_id:
            events = self._logger.get_events(execution_id, limit=1000)
        elif action:
            events = self._logger.get_events_by_action(action, limit=1000)
        else:
            events = self._logger.get_all_events(limit=1000)

        result = []
        for e in events:
            if action and e.action != action:
                continue
            if stage_name and e.stage_name != stage_name:
                continue
            if status and e.status != status:
                continue
            result.append({
                "event_id": e.event_id,
                "timestamp": e.timestamp,
                "execution_id": e.execution_id[:8],
                "stage": e.stage_name,
                "action": e.action,
                "status": e.status,
                "duration_ms": e.duration_ms,
                "error": e.error[:100] if e.error else "",
            })
            if len(result) >= limit:
                break

        return result
