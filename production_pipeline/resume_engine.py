"""Resume Engine — auto-resume pipeline execution from the last checkpoint.

On restart or crash, scans for incomplete workflows and resumes them
from the last successful checkpoint. Never repeats completed stages.
Target: <5s resume time.
"""

from __future__ import annotations

import logging
from typing import Any

from production_pipeline.checkpoint_manager import CheckpointManager
from production_pipeline.config import PipelineHardeningConfig
from production_pipeline.constants import STAGE_NAMES, WorkflowState
from production_pipeline.exceptions import ResumeError
from production_pipeline.models import PipelineCheckpoint
from production_pipeline.state_machine import WorkflowStateMachine

logger = logging.getLogger(__name__)


class ResumeEngine:
    """Auto-resume pipeline execution from the last checkpoint.

    Determines the next stage to run by comparing completed checkpoints
    against the full stage list. Rebuilds execution context from checkpoints.
    Never repeats completed stages.
    """

    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        config: PipelineHardeningConfig | None = None,
    ) -> None:
        self._checkpoints = checkpoint_manager
        self._config = config or PipelineHardeningConfig()

    def find_resumable_workflows(
        self, active_executions: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Find workflows that can be resumed from their last checkpoint.

        Args:
            active_executions: Dict of execution_id -> execution state.

        Returns:
            List of resumable workflow summaries.
        """
        resumable = []
        for exec_id, state in active_executions.items():
            wf_state = state.get("workflow_state", "")
            if wf_state in (
                WorkflowState.RUNNING.value,
                WorkflowState.RECOVERING.value,
                WorkflowState.RETRYING.value,
                WorkflowState.FAILED.value,
            ):
                checkpoints = self._checkpoints.list_checkpoints(exec_id)
                if checkpoints:
                    resumable.append({
                        "execution_id": exec_id,
                        "state": wf_state,
                        "checkpoints": len(checkpoints),
                        "last_stage": checkpoints[-1].stage_name,
                    })
        return resumable

    def determine_next_stage(
        self, execution_id: str, stages: list[str] | None = None
    ) -> str | None:
        """Determine the next stage to run based on completed checkpoints.

        Args:
            execution_id: Workflow execution ID.
            stages: Full ordered list of stage names (uses default if None).

        Returns:
            Name of the next stage to run, or None if all stages are complete.
        """
        stages = stages or STAGE_NAMES
        completed = self._checkpoints.get_completed_stages(execution_id)

        for stage in stages:
            if stage not in completed:
                return stage

        return None  # All stages complete

    def rebuild_context(
        self, execution_id: str
    ) -> dict[str, Any]:
        """Rebuild the full execution context from all checkpoints.

        Args:
            execution_id: Workflow execution ID.

        Returns:
            Full pipeline context dict with all stage outputs merged.
        """
        return self._checkpoints.rebuild_pipeline_state(execution_id)

    def resume(
        self,
        execution_id: str,
        execution_state: dict[str, Any],
        stages: list[str] | None = None,
    ) -> dict[str, Any]:
        """Resume a pipeline execution from its last checkpoint.

        Args:
            execution_id: Workflow execution ID.
            execution_state: Current execution state.
            stages: Full ordered list of stage names.

        Returns:
            Resume result with next stage and context.

        Raises:
            ResumeError: If resume is not possible.
        """
        stages = stages or STAGE_NAMES
        completed = self._checkpoints.get_completed_stages(execution_id)

        # Check if all stages are already complete
        if len(completed) >= len(stages):
            return {
                "execution_id": execution_id,
                "status": "already_completed",
                "completed_stages": completed,
                "next_stage": None,
            }

        # Determine next stage
        next_stage = self.determine_next_stage(execution_id, stages)
        if next_stage is None:
            return {
                "execution_id": execution_id,
                "status": "already_completed",
                "completed_stages": completed,
                "next_stage": None,
            }

        # Rebuild execution context
        context = self.rebuild_context(execution_id)

        result = {
            "execution_id": execution_id,
            "status": "resumed",
            "previous_state": execution_state.get("workflow_state", "unknown"),
            "completed_stages": completed,
            "next_stage": next_stage,
            "remaining_stages": stages[len(completed):],
            "completed_count": len(completed),
            "total_stages": len(stages),
            "context": context,
        }

        logger.info(
            "Pipeline resumed: execution=%s completed=%d/%d next=%s",
            execution_id[:8], len(completed), len(stages), next_stage,
        )

        return result

    def get_resume_point(
        self, execution_id: str
    ) -> PipelineCheckpoint | None:
        """Get the checkpoint to resume from (the last successful one).

        Args:
            execution_id: Workflow execution ID.

        Returns:
            The last ``PipelineCheckpoint``, or None.
        """
        return self._checkpoints.get_last_checkpoint(execution_id)

    def has_completed_stage(
        self, execution_id: str, stage_name: str
    ) -> bool:
        """Check if a specific stage has already completed.

        Args:
            execution_id: Workflow execution ID.
            stage_name: Stage name to check.

        Returns:
            True if the stage has a checkpoint.
        """
        return self._checkpoints.get_checkpoint(execution_id, stage_name) is not None
