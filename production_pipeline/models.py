"""Pydantic models for Production Pipeline Hardening."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from production_pipeline.constants import (
    ErrorClass,
    StageState as StageStateEnum,
    WorkflowState as WorkflowStateEnum,
)


class WorkflowExecution(BaseModel):
    """Full execution context for a durable workflow."""
    execution_id: str = ""
    project_id: str = ""
    video_id: str = ""
    workflow_state: WorkflowStateEnum = WorkflowStateEnum.CREATED
    current_stage: str = ""
    completed_stages: list[str] = Field(default_factory=list)
    failed_stages: list[dict[str, Any]] = Field(default_factory=list)
    retry_count: int = 0
    recovery_count: int = 0
    total_duration_ms: float = 0.0
    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: str = ""
    error: str = ""
    correlation_id: str = ""
    trace_id: str = ""
    worker_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowStage(BaseModel):
    """Per-stage execution record."""
    stage_id: str = ""
    execution_id: str = ""
    stage_name: str = ""
    state: StageStateEnum = StageStateEnum.PENDING
    input_hash: str = ""
    output_hash: str = ""
    duration_ms: float = 0.0
    retry_count: int = 0
    error: str = ""
    error_class: str = ""
    checkpoint_id: str = ""
    snapshot_id: str = ""
    started_at: str = ""
    completed_at: str = ""
    worker_id: str = ""
    provider: str = ""
    model: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineCheckpoint(BaseModel):
    """Durable checkpoint snapshot after a stage."""
    checkpoint_id: str = ""
    execution_id: str = ""
    stage_name: str = ""
    stage_index: int = 0
    status: str = ""
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    input_hash: str = ""
    output_hash: str = ""
    duration_ms: float = 0.0
    retry_count: int = 0
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class StageSnapshot(BaseModel):
    """Immutable stage snapshot with content integrity."""
    snapshot_id: str = ""
    execution_id: str = ""
    stage_name: str = ""
    content_hash: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    prompt: str = ""
    model: str = ""
    provider: str = ""
    temperature: float = 0.0
    generated_files: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    logs: list[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class IdempotencyKey(BaseModel):
    """Idempotency execution key record."""
    key: str = ""
    execution_id: str = ""
    stage_name: str = ""
    input_hash: str = ""
    output_hash: str = ""
    status: str = "completed"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    expires_at: str = ""


class ExecutionEvent(BaseModel):
    """Immutable transaction log entry."""
    event_id: str = ""
    execution_id: str = ""
    stage_name: str = ""
    action: str = ""
    status: str = ""
    request_id: str = ""
    correlation_id: str = ""
    trace_id: str = ""
    worker_id: str = ""
    duration_ms: float = 0.0
    retry_count: int = 0
    error: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class DeadLetterRecord(BaseModel):
    """Dead letter queue entry for failed pipelines."""
    dlq_id: str = ""
    execution_id: str = ""
    project_id: str = ""
    stage_name: str = ""
    error: str = ""
    error_class: str = ""
    traceback: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    retry_history: list[dict[str, Any]] = Field(default_factory=list)
    recovery_status: str = "pending"
    recovered_at: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class TimeoutConfig(BaseModel):
    """Per-stage timeout configuration."""
    stage_name: str = ""
    timeout_seconds: int = 30
    action: str = "retry"
    max_retries: int = 2


class ValidationResult(BaseModel):
    """Stage validation result."""
    passed: bool = True
    stage_name: str = ""
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    input_valid: bool = True
    output_valid: bool = True
    dependencies_valid: bool = True
