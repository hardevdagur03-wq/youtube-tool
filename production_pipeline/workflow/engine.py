"""Durable Workflow Engine — wraps the existing PipelineOrchestrator with durability.

Provides Temporal-like durable execution guarantees: checkpointing after every
stage, automatic resume from failures, idempotency enforcement, crash recovery,
and full execution history. Wraps PipelineOrchestrator via composition.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Callable

from production_pipeline.checkpoint_manager import CheckpointManager
from production_pipeline.config import PipelineHardeningConfig
from production_pipeline.constants import STAGE_NAMES, WorkflowState
from production_pipeline.dead_letter_queue import PipelineDeadLetterQueue
from production_pipeline.error_handler import ErrorHandler
from production_pipeline.execution_history import ExecutionHistory
from production_pipeline.idempotency import IdempotencyFramework
from production_pipeline.recovery_manager import RecoveryManager
from production_pipeline.resume_engine import ResumeEngine
from production_pipeline.snapshot_manager import SnapshotManager
from production_pipeline.state_machine import WorkflowStateMachine, StageStateMachine
from production_pipeline.stage_validator import StageValidator
from production_pipeline.timeout_manager import TimeoutManager
from production_pipeline.transaction_logger import TransactionLogger
from production_pipeline.retry_framework import RetryFramework

logger = logging.getLogger(__name__)


class DurableWorkflowEngine:
    """Durable workflow engine wrapping the existing PipelineOrchestrator.

    Provides:
    - Checkpointing after every stage
    - Automatic resume from last checkpoint
    - Idempotent stage execution
    - Crash recovery
    - Full execution history
    - Per-stage timeouts
    - Dead letter queue for failed stages
    - State machine validation

    Usage::

        engine = DurableWorkflowEngine()
        engine.register_stage_executor("metadata", executor_fn)
        result = await engine.run_workflow(execution_id, video_id="...")
    """

    def __init__(
        self,
        config: PipelineHardeningConfig | None = None,
        checkpoint_manager: CheckpointManager | None = None,
        snapshot_manager: SnapshotManager | None = None,
        idempotency: IdempotencyFramework | None = None,
        transaction_logger: TransactionLogger | None = None,
        execution_history: ExecutionHistory | None = None,
        error_handler: ErrorHandler | None = None,
        retry_framework: RetryFramework | None = None,
        timeout_manager: TimeoutManager | None = None,
        dead_letter_queue: PipelineDeadLetterQueue | None = None,
        recovery_manager: RecoveryManager | None = None,
        resume_engine: ResumeEngine | None = None,
        stage_validator: StageValidator | None = None,
        state_machine: WorkflowStateMachine | None = None,
    ) -> None:
        self._config = config or PipelineHardeningConfig()
        self._checkpoints = checkpoint_manager or CheckpointManager(self._config)
        self._snapshots = snapshot_manager or SnapshotManager(self._config)
        self._idempotency = idempotency or IdempotencyFramework(self._config)
        self._tx_log = transaction_logger or TransactionLogger(self._config)
        self._exec_history = execution_history or ExecutionHistory(self._tx_log)
        self._error_handler = error_handler or ErrorHandler()
        self._retry = retry_framework or RetryFramework(self._config)
        self._timeout = timeout_manager or TimeoutManager(self._config)
        self._dlq = dead_letter_queue or PipelineDeadLetterQueue(self._config)
        self._recovery = recovery_manager or RecoveryManager(self._config)
        self._resume = resume_engine or ResumeEngine(self._checkpoints, self._config)
        self._validator = stage_validator or StageValidator()
        self._state = state_machine or WorkflowStateMachine()

        # Registered stage executors: name -> callable
        self._stage_executors: dict[str, Callable] = {}
        # Active executions: execution_id -> state
        self._executions: dict[str, dict[str, Any]] = {}

    def register_stage_executor(
        self, stage_name: str, executor_fn: Callable
    ) -> None:
        """Register a stage executor function.

        Args:
            stage_name: Stage name (e.g. 'metadata', 'transcript').
            executor_fn: Async callable that takes (context) and returns dict.
        """
        self._stage_executors[stage_name] = executor_fn
        logger.debug("Stage executor registered: %s", stage_name)

    async def run_workflow(
        self,
        execution_id: str,
        video_id: str = "",
        project_id: str = "",
        stages: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run a full workflow with durable execution guarantees.

        Args:
            execution_id: Unique execution ID.
            video_id: YouTube video ID.
            project_id: Project ID.
            stages: Ordered list of stage names (defaults to all stages).

        Returns:
            Workflow result dict.
        """
        stages = stages or STAGE_NAMES
        start_time = time.time()

        # Initialize execution state
        execution_state = {
            "execution_id": execution_id,
            "video_id": video_id,
            "project_id": project_id,
            "workflow_state": WorkflowState.CREATED.value,
            "started_at": time.time(),
            "last_update": time.time(),
        }
        self._executions[execution_id] = execution_state

        # Create workflow execution
        self._state = WorkflowStateMachine(WorkflowState.CREATED)
        self._state.transition_to(WorkflowState.QUEUED)

        self._tx_log.log_event(
            execution_id, "workflow_started", status="queued",
            details={"video_id": video_id, "project_id": project_id},
        )

        # Check for existing checkpoints (resume path)
        completed_stages = self._checkpoints.get_completed_stages(execution_id)

        if completed_stages:
            logger.info(
                "Workflow %s: resuming from checkpoint. "
                "%d/%d stages already completed.",
                execution_id[:8], len(completed_stages), len(stages),
            )

        # Run stages sequentially
        self._state.transition_to(WorkflowState.RUNNING)
        execution_state["workflow_state"] = WorkflowState.RUNNING.value

        for stage_index, stage_name in enumerate(stages):
            # Skip if already completed (from checkpoint)
            if stage_name in completed_stages:
                logger.info(
                    "Skipping already completed stage: %s",
                    stage_name,
                )
                continue

            # Execute stage with all durability features
            result = await self._execute_stage(
                execution_id, stage_name, stage_index,
                execution_state,
            )

            if not result["success"]:
                execution_state["workflow_state"] = WorkflowState.FAILED.value
                elapsed = time.time() - start_time
                self._tx_log.log_event(
                    execution_id, "workflow_failed",
                    stage_name=stage_name, status="failed",
                    duration_ms=round(elapsed * 1000),
                    error=result.get("error", ""),
                )
                return {
                    "success": False,
                    "execution_id": execution_id,
                    "failed_stage": stage_name,
                    "error": result.get("error", "Unknown error"),
                    "completed_stages": self._checkpoints.get_completed_stages(execution_id),
                    "duration_ms": round(elapsed * 1000),
                }

            # Update execution state
            execution_state["last_update"] = time.time()

        # Mark workflow as completed
        self._state.transition_to(WorkflowState.COMPLETED)
        execution_state["workflow_state"] = WorkflowState.COMPLETED.value
        elapsed = time.time() - start_time

        self._tx_log.log_event(
            execution_id, "workflow_completed", status="completed",
            duration_ms=round(elapsed * 1000),
            details={
                "total_stages": len(stages),
                "completed_stages": len(self._checkpoints.get_completed_stages(execution_id)),
            },
        )

        logger.info(
            "Workflow %s completed: %d stages in %.1fs",
            execution_id[:8], len(stages), elapsed,
        )

        return {
            "success": True,
            "execution_id": execution_id,
            "completed_stages": self._checkpoints.get_completed_stages(execution_id),
            "duration_ms": round(elapsed * 1000),
        }

    async def _execute_stage(
        self,
        execution_id: str,
        stage_name: str,
        stage_index: int,
        execution_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a single stage with all durability features.

        Flow:
        1. Validate stage inputs
        2. Check idempotency (skip if already completed)
        3. Create stage state machine
        4. Execute with timeout + retry
        5. Validate outputs
        6. Save checkpoint
        7. Save snapshot
        8. Log transaction
        9. Mark idempotency key as completed
        """
        executor = self._stage_executors.get(stage_name)
        if executor is None:
            return {"success": False, "error": f"No executor for stage '{stage_name}'"}

        # Get pipeline context from checkpoints
        context = self._checkpoints.rebuild_pipeline_state(execution_id)
        # Inject top-level context
        if execution_state.get("video_id"):
            context["video_id"] = execution_state["video_id"]
        if execution_state.get("project_id"):
            context["project_id"] = execution_state["project_id"]

        # Step 1: Validate inputs
        input_valid = self._validator.validate_input(stage_name, context)
        if not input_valid.passed:
            error_msg = f"Input validation failed: {'; '.join(input_valid.errors)}"
            self._tx_log.log_event(
                execution_id, "stage_validation_failed",
                stage_name=stage_name, status="failed", error=error_msg,
            )
            return {"success": False, "error": error_msg}

        # Step 2: Check idempotency
        is_dup, _, warning = self._idempotency.check_and_register(
            execution_id, stage_name, context,
        )
        if is_dup:
            self._tx_log.log_event(
                execution_id, "stage_skipped_duplicate",
                stage_name=stage_name, status="skipped",
                error=warning or "Duplicate execution blocked",
            )
            return {"success": True, "skipped": True, "reason": warning}

        # Step 3: Create stage state machine
        from production_pipeline.constants import StageState as StageStateEnum
        stage_sm = StageStateMachine()
        stage_sm.transition_to(StageStateEnum.READY)
        stage_sm.transition_to(StageStateEnum.RUNNING)

        self._tx_log.log_event(
            execution_id, "stage_started",
            stage_name=stage_name, status="running",
        )

        # Step 4: Execute with timeout
        stage_start = time.time()
        try:
            output = await self._timeout.enforce_timeout_async(
                stage_name,
                executor(context),
            )
            stage_duration = (time.time() - stage_start) * 1000

        except Exception as exc:
            stage_duration = (time.time() - stage_start) * 1000
            handled = self._error_handler.handle(exc, stage_name, execution_id)

            # Determine retry
            should_retry, delay, reason = self._retry.should_retry(
                exc, attempt=1,
                execution_id=execution_id, stage_name=stage_name,
            )

            self._idempotency.mark_failed(execution_id, stage_name, context)

            if should_retry:
                self._tx_log.log_event(
                    execution_id, "stage_retrying",
                    stage_name=stage_name, status="retrying",
                    duration_ms=round(stage_duration),
                    error=str(exc)[:200],
                    details={"retry_delay": delay, "reason": reason},
                )
                return {"success": False, "error": str(exc), "retryable": True}

            # Check if should go to DLQ
            if handled.get("recoverable", False):
                self._dlq.send(
                    execution_id, execution_state.get("project_id", ""),
                    stage_name, exc, context,
                    retry_count=1,
                )

            self._tx_log.log_event(
                execution_id, "stage_failed",
                stage_name=stage_name, status="failed",
                duration_ms=round(stage_duration),
                error=str(exc)[:500],
            )
            return {"success": False, "error": str(exc)}

        # Step 5: Validate outputs
        if isinstance(output, dict):
            output_valid = self._validator.validate_output(stage_name, output)
            if not output_valid.passed:
                error_msg = f"Output validation failed: {'; '.join(output_valid.errors)}"
                self._tx_log.log_event(
                    execution_id, "stage_output_invalid",
                    stage_name=stage_name, status="failed", error=error_msg,
                )
                return {"success": False, "error": error_msg}

        # Step 6: Save checkpoint
        cp_output = output if isinstance(output, dict) else {"result": str(output)}
        self._checkpoints.save_checkpoint(
            execution_id, stage_name, stage_index,
            input_data=context,
            output_data=cp_output,
            duration_ms=round(stage_duration),
        )

        # Step 7: Save snapshot (if enabled)
        if self._config.snapshot_enabled:
            self._snapshots.create_snapshot(
                execution_id, stage_name,
                inputs=context,
                outputs=cp_output,
                provider="",
                model="",
            )

        # Step 8: Mark idempotency as completed
        self._idempotency.mark_completed(
            execution_id, stage_name, context, cp_output,
        )

        # Step 9: Log transaction
        self._tx_log.log_event(
            execution_id, "stage_completed",
            stage_name=stage_name, status="completed",
            duration_ms=round(stage_duration),
        )

        return {"success": True, "output": output}

    async def resume_workflow(
        self, execution_id: str
    ) -> dict[str, Any]:
        """Resume a workflow from its last checkpoint.

        Args:
            execution_id: Execution ID to resume.

        Returns:
            Workflow result dict.
        """
        execution_state = self._executions.get(execution_id, {})
        if not execution_state:
            return {"success": False, "error": f"Execution '{execution_id}' not found"}

        resume_result = self._resume.resume(execution_id, execution_state)
        if resume_result["status"] == "already_completed":
            return {"success": True, "already_completed": True}

        # Resume from next stage
        next_stage = resume_result["next_stage"]
        stages = STAGE_NAMES
        start_index = stages.index(next_stage) if next_stage in stages else 0

        self._tx_log.log_event(
            execution_id, "workflow_resumed",
            status="recovering",
            details={
                "next_stage": next_stage,
                "completed_stages": resume_result["completed_stages"],
            },
        )

        return await self.run_workflow(
            execution_id,
            stages=stages[start_index:],
        )

    async def cancel_workflow(self, execution_id: str) -> bool:
        """Cancel a running workflow.

        Args:
            execution_id: Execution ID.

        Returns:
            True if cancelled.
        """
        if execution_id in self._executions:
            self._executions[execution_id]["workflow_state"] = WorkflowState.CANCELLED.value
            self._tx_log.log_event(execution_id, "workflow_cancelled", status="cancelled")
            return True
        return False

    def get_workflow_status(self, execution_id: str) -> dict[str, Any] | None:
        """Get the current status of a workflow execution.

        Args:
            execution_id: Execution ID.

        Returns:
            Execution state dict or None.
        """
        state = self._executions.get(execution_id)
        if state is None:
            return None
        return {
            "execution_id": execution_id,
            "state": state.get("workflow_state"),
            "completed_stages": self._checkpoints.get_completed_stages(execution_id),
            "checkpoint_count": self._checkpoints.checkpoint_count(execution_id),
        }
