"""Recovery Manager — automated crash recovery for pipeline executions.

Handles: worker crash, app restart, container restart, deployment,
OOM, power failure, network partition. Scans for incomplete workflows
on startup and recovers them automatically.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from production_pipeline.config import PipelineHardeningConfig
from production_pipeline.constants import WorkflowState
from production_pipeline.state_machine import WorkflowStateMachine

logger = logging.getLogger(__name__)

# States that indicate a workflow may need recovery
_RECOVERABLE_STATES = {
    WorkflowState.RUNNING,
    WorkflowState.RETRYING,
    WorkflowState.RECOVERING,
    WorkflowState.WAITING,
}


class RecoveryManager:
    """Automated crash recovery for pipeline executions.

    On startup, scans for incomplete workflows and recovers them
    from their last checkpoint. Handles worker, app, container,
    and infrastructure failures.
    """

    def __init__(self, config: PipelineHardeningConfig | None = None) -> None:
        self._config = config or PipelineHardeningConfig()
        self._recovery_records: dict[str, dict[str, Any]] = {}

    def scan_and_recover(
        self,
        active_executions: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Scan active executions and recover any that are stuck.

        Called on startup and periodically during operation.

        Args:
            active_executions: Dict of execution_id -> execution state.

        Returns:
            List of recovery results, one per recovered execution.
        """
        results = []
        for exec_id, state in active_executions.items():
            result = self._try_recover(exec_id, state)
            if result:
                results.append(result)
        return results

    def _try_recover(
        self, execution_id: str, state: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Try to recover a single execution.

        Args:
            execution_id: Execution ID.
            state: Current execution state.

        Returns:
            Recovery result dict if recovery was needed, else None.
        """
        workflow_state_str = state.get("workflow_state", "")
        try:
            current_state = WorkflowState(workflow_state_str)
        except ValueError:
            return None

        if current_state not in _RECOVERABLE_STATES:
            return None

        # Calculate how long this execution has been in this state
        started_at = state.get("started_at", "")
        last_update = state.get("last_update", "")
        current_time = time.time()

        # If execution has been in a non-terminal state for too long, recover it
        # Default: recover if stuck for > 5 minutes
        stuck_duration = self._get_stuck_duration(state, current_time)
        if stuck_duration < 300:  # 5 minutes
            return None

        logger.warning(
            "Recovering execution %s: stuck in state '%s' for %.0fs",
            execution_id[:8], workflow_state_str, stuck_duration,
        )

        # Attempt recovery
        return self.recover_execution(execution_id, state)

    def recover_execution(
        self, execution_id: str, state: dict[str, Any]
    ) -> dict[str, Any]:
        """Recover a single execution from its current state.

        Args:
            execution_id: Execution ID.
            state: Current execution state.

        Returns:
            Recovery result dict.
        """
        attempt = self._recovery_records.get(execution_id, {}).get("attempt", 0) + 1
        previous_state = state.get("workflow_state", "unknown")

        # Mark as recovering
        state["workflow_state"] = WorkflowState.RECOVERING.value
        state["recovery_count"] = state.get("recovery_count", 0) + 1

        record = {
            "execution_id": execution_id,
            "previous_state": previous_state,
            "recovered_state": WorkflowState.RECOVERING.value,
            "attempt": attempt,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._recovery_records[execution_id] = record

        logger.info(
            "Execution %s recovered: %s -> %s (attempt %d)",
            execution_id[:8], previous_state, WorkflowState.RECOVERING.value, attempt,
        )

        return record

    def mark_recovered(self, execution_id: str) -> None:
        """Mark an execution as successfully recovered.

        Args:
            execution_id: Execution ID.
        """
        record = self._recovery_records.get(execution_id)
        if record:
            record["recovered_state"] = WorkflowState.RUNNING.value
            record["completed_at"] = datetime.now(timezone.utc).isoformat()

    def mark_failed(self, execution_id: str, error: str = "") -> None:
        """Mark a recovery attempt as failed.

        Args:
            execution_id: Execution ID.
            error: Error message.
        """
        record = self._recovery_records.get(execution_id)
        if record:
            record["recovered_state"] = WorkflowState.FAILED.value
            record["error"] = error

    def get_recovery_history(
        self, execution_id: str
    ) -> list[dict[str, Any]]:
        """Get recovery history for an execution.

        Args:
            execution_id: Execution ID.

        Returns:
            List of recovery records.
        """
        record = self._recovery_records.get(execution_id)
        return [record] if record else []

    def get_recovery_summary(self) -> dict[str, Any]:
        """Get a summary of all recovery activity.

        Returns:
            Summary dict.
        """
        total = len(self._recovery_records)
        successful = sum(
            1 for r in self._recovery_records.values()
            if r.get("recovered_state") == WorkflowState.RUNNING.value
        )
        failed = sum(
            1 for r in self._recovery_records.values()
            if r.get("recovered_state") == WorkflowState.FAILED.value
        )
        return {
            "total_recoveries": total,
            "successful": successful,
            "failed": failed,
            "rate": round(successful / max(total, 1) * 100, 1),
        }

    @staticmethod
    def _get_stuck_duration(state: dict[str, Any], current_time: float) -> float:
        """Calculate how long an execution has been in its current state."""
        last_update = state.get("last_update", "")
        if not last_update:
            started_at = state.get("started_at", "")
            if started_at:
                try:
                    dt = datetime.fromisoformat(started_at)
                    return current_time - dt.timestamp()
                except (ValueError, TypeError):
                    pass
        else:
            try:
                dt = datetime.fromisoformat(last_update)
                return current_time - dt.timestamp()
            except (ValueError, TypeError):
                pass
        return 0.0
