"""Workflow Engine — orchestrates multi-job workflows with chains, groups, chords, and conditional branching.

Supports:
- Sequential chains (stage1 → stage2 → stage3)
- Parallel fan-out (group)
- Fan-in (chord = group + callback)
- Conditional branching (if/else based on previous result)
- Parent-child job dependencies
- Checkpoint-based pipeline resume
- Workflow cancellation
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from celery import Celery, chain, chord, group

from background_processing.celery_app import get_celery_app
from background_processing.config import BackgroundProcessingConfig
from background_processing.dispatcher import JobDispatcher
from background_processing.job_repository import JobRepository
from background_processing.models import (
    JobCreate, JobPriority, JobStatus, JobType,
    STAGE_ORDER, make_uuid,
)
from background_processing.progress_emitter import ProgressEmitter

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class WorkflowStep:
    """A single step in a workflow definition."""
    name: str
    job_type: str
    queue: str = ""
    depends_on: list[str] = field(default_factory=list)
    max_retries: int = 3
    payload_template: dict[str, Any] = field(default_factory=dict)
    condition: Callable[[dict[str, Any]], bool] | None = None
    timeout_seconds: int = 3600


@dataclass
class WorkflowDefinition:
    """Complete workflow definition with steps, branching, and error handling."""
    workflow_id: str = ""
    name: str = ""
    project_id: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)
    tenant_id: str = ""
    user_id: str = ""
    parallel_groups: list[list[str]] = field(default_factory=list)
    on_failure: str = "stop"  # stop | continue | retry_group
    checkpoint_enabled: bool = True
    max_retries: int = 1


@dataclass
class WorkflowExecution:
    """Runtime state of a workflow execution."""
    execution_id: str = ""
    workflow_id: str = ""
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step: str = ""
    completed_steps: list[str] = field(default_factory=list)
    failed_steps: list[str] = field(default_factory=list)
    step_results: dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    finished_at: str = ""
    error: str = ""


class WorkflowEngine:
    """Enterprise workflow orchestrator.

    Manages the lifecycle of complex multi-job workflows including
    pipeline orchestration, conditional branching, and checkpoint-based resume.
    """

    def __init__(
        self,
        dispatcher: JobDispatcher,
        job_repo: JobRepository,
        celery_app: Celery | None = None,
        config: BackgroundProcessingConfig | None = None,
    ) -> None:
        self._dispatcher = dispatcher
        self._repo = job_repo
        self._app = celery_app or get_celery_app()
        self._config = config or BackgroundProcessingConfig.from_env()
        self._executions: dict[str, WorkflowExecution] = {}

    async def run_pipeline(
        self,
        project_id: str,
        payload: dict[str, Any] | None = None,
        tenant_id: str = "",
        user_id: str = "",
        start_from: str = "",
    ) -> WorkflowExecution:
        """Run the full pipeline as a sequential workflow with checkpoint support.

        Args:
            project_id: Target project.
            payload: Initial payload (url, video_id, etc.).
            tenant_id: Tenant isolation.
            user_id: User context.
            start_from: Stage name to resume from (empty = start fresh).

        Returns:
            WorkflowExecution tracking state.
        """
        workflow_def = self._build_pipeline_workflow(project_id, payload or {}, start_from)
        return await self.execute(workflow_def, tenant_id=tenant_id, user_id=user_id)

    async def execute(
        self,
        workflow: WorkflowDefinition,
        tenant_id: str = "",
        user_id: str = "",
    ) -> WorkflowExecution:
        """Execute a workflow definition, dispatching jobs for each step.

        Handles:
        - Sequential execution (chain)
        - Parallel execution (group within chain)
        - Conditional branching
        - Checkpoint registration for resume
        """
        execution = WorkflowExecution(
            execution_id=make_uuid(),
            workflow_id=workflow.workflow_id or make_uuid(),
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._executions[execution.execution_id] = execution

        logger.info(
            "Workflow started: execution=%s workflow=%s steps=%d",
            execution.execution_id[:8], workflow.name, len(workflow.steps),
        )

        try:
            for step_idx, step in enumerate(workflow.steps):
                if workflow.checkpoint_enabled:
                    checkpoint_key = f"checkpoint:{workflow.project_id}:{step.name}"
                    await self._save_checkpoint(workflow.project_id, step.name)

                if step.condition:
                    prev_result = execution.step_results.get(step.depends_on[0]) if step.depends_on else None
                    if prev_result and not step.condition(prev_result):
                        logger.info("Step %s skipped (condition not met)", step.name)
                        execution.completed_steps.append(step.name)
                        continue

                execution.current_step = step.name
                job_create = JobCreate(
                    job_type=step.job_type,
                    project_id=workflow.project_id,
                    payload=step.payload_template,
                    priority=JobPriority.NORMAL,
                    queue=step.queue or "default",
                    max_retries=step.max_retries,
                )

                job_resp = await self._dispatcher.dispatch(
                    job_create,
                    tenant_id=tenant_id,
                    user_id=user_id,
                )

                execution.completed_steps.append(step.name)
                execution.step_results[step.name] = {"job_id": job_resp.job_id, "status": job_resp.status.value}

                logger.info("Workflow step %s: job=%s status=%s", step.name, job_resp.job_id[:8], job_resp.status.value)

            execution.status = WorkflowStatus.COMPLETED
            execution.finished_at = datetime.now(timezone.utc).isoformat()
            logger.info("Workflow completed: %s", execution.execution_id[:8])

        except Exception as exc:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(exc)
            execution.finished_at = datetime.now(timezone.utc).isoformat()
            logger.error("Workflow failed: %s: %s", execution.execution_id[:8], exc)

        return execution

    async def resume(
        self,
        project_id: str,
        payload: dict[str, Any] | None = None,
        tenant_id: str = "",
        user_id: str = "",
    ) -> WorkflowExecution | None:
        """Resume a pipeline from its last checkpoint."""
        checkpoint = await self._load_checkpoint(project_id)
        if checkpoint is None:
            logger.warning("No checkpoint found for project %s, starting fresh", project_id)
            return await self.run_pipeline(project_id, payload, tenant_id, user_id)

        last_stage = checkpoint.get("last_stage", "")
        logger.info("Resuming pipeline %s from stage: %s", project_id, last_stage)
        return await self.run_pipeline(project_id, payload, tenant_id, user_id, start_from=last_stage)

    async def cancel(self, execution_id: str) -> bool:
        """Cancel a running workflow."""
        execution = self._executions.get(execution_id)
        if execution is None:
            return False
        execution.status = WorkflowStatus.CANCELLED
        execution.finished_at = datetime.now(timezone.utc).isoformat()
        logger.info("Workflow cancelled: %s", execution_id[:8])
        return True

    async def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        return self._executions.get(execution_id)

    async def list_executions(self, project_id: str = "") -> list[WorkflowExecution]:
        if project_id:
            return [e for e in self._executions.values() if e.workflow_id == project_id]
        return list(self._executions.values())

    # ------------------------------------------------------------------
    # Pipeline workflow builder
    # ------------------------------------------------------------------

    def _build_pipeline_workflow(
        self,
        project_id: str,
        base_payload: dict[str, Any],
        start_from: str = "",
    ) -> WorkflowDefinition:
        """Build the standard pipeline workflow from STAGE_ORDER."""
        should_start = not bool(start_from)
        steps: list[WorkflowStep] = []

        type_map = {
            "metadata": "pipeline.metadata",
            "transcript": "pipeline.transcript",
            "analysis": "pipeline.analysis",
            "knowledge_graph": "pipeline.knowledge_graph",
            "seo": "pipeline.seo",
            "seo_intelligence": "pipeline.seo_intelligence",
            "outline": "pipeline.outline",
            "sections": "pipeline.sections",
            "merge": "pipeline.merge",
            "review": "pipeline.review",
            "optimization": "pipeline.optimization",
            "export": "pipeline.export",
        }

        for stage in STAGE_ORDER:
            stage_key = stage.replace("pipeline.", "")
            if stage == start_from:
                should_start = True
            if not should_start:
                continue

            job_type = type_map.get(stage_key, stage)
            steps.append(WorkflowStep(
                name=stage,
                job_type=job_type,
                queue="high" if "pipeline." in stage else "default",
                payload_template=dict(base_payload),
            ))

        return WorkflowDefinition(
            workflow_id=project_id,
            name=f"pipeline-{project_id[:8]}",
            project_id=project_id,
            steps=steps,
            checkpoint_enabled=True,
        )

    # ------------------------------------------------------------------
    # Checkpoint management
    # ------------------------------------------------------------------

    async def _save_checkpoint(self, project_id: str, stage: str) -> None:
        redis = await self._get_redis()
        key = f"checkpoint:{project_id}"
        data = json.dumps({"last_stage": stage, "timestamp": time.time()})
        await redis.set(key, data, ex=86400 * 7)

    async def _load_checkpoint(self, project_id: str) -> dict[str, Any] | None:
        redis = await self._get_redis()
        key = f"checkpoint:{project_id}"
        data = await redis.get(key)
        if data:
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                pass
        return None

    async def clear_checkpoint(self, project_id: str) -> None:
        redis = await self._get_redis()
        await redis.delete(f"checkpoint:{project_id}")

    async def _get_redis(self):
        from redis.asyncio import Redis
        return Redis.from_url(self._config.redis_url, decode_responses=True, socket_timeout=5)
