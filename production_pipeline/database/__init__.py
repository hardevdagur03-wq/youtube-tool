"""Database models for Production Pipeline Hardening — 12 new tables."""

from __future__ import annotations

from typing import Any

from sqlalchemy import BigInteger, Boolean, Float, Integer, String, Text, func
from sqlalchemy import JSON as SA_JSON
from sqlalchemy.orm import Mapped, mapped_column

from database.base import BaseModel


class WorkflowExecutionModel(BaseModel):
    """Durable workflow execution records."""

    __tablename__ = "workflow_executions"

    execution_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True
    )
    project_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    video_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", index=True
    )
    workflow_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default="created"
    )
    current_stage: Mapped[str] = mapped_column(
        String(64), nullable=False, default=""
    )
    completed_stages: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    failed_stages: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recovery_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    worker_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )

    def __repr__(self) -> str:
        return (
            f"<WorkflowExecutionModel id={self.execution_id} "
            f"state={self.workflow_state} project={self.project_id}>"
        )


class WorkflowStageModel(BaseModel):
    """Per-stage execution records."""

    __tablename__ = "workflow_stages"

    stage_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True
    )
    execution_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error_class: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    checkpoint_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    snapshot_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    worker_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    model: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )


class PipelineCheckpointModel(BaseModel):
    """DB-backed durable checkpoint snapshots."""

    __tablename__ = "pipeline_checkpoints"

    checkpoint_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True
    )
    execution_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    stage_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    input_data: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    output_data: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class StageSnapshotModel(BaseModel):
    """Immutable stage output snapshots."""

    __tablename__ = "stage_snapshots"

    snapshot_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True
    )
    execution_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    inputs: Mapped[dict[str, Any]] = mapped_column(SA_JSON, nullable=False, default=dict)
    outputs: Mapped[dict[str, Any]] = mapped_column(SA_JSON, nullable=False, default=dict)
    prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    model: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    generated_files: Mapped[list[str]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    logs: Mapped[list[str]] = mapped_column(SA_JSON, nullable=False, default=list)


class IdempotencyKeyModel(BaseModel):
    """Idempotency execution key records."""

    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    execution_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    expires_at: Mapped[str] = mapped_column(String(32), nullable=False, default="")


class ExecutionEventModel(BaseModel):
    """Immutable transaction log entries."""

    __tablename__ = "execution_history"

    event_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True
    )
    execution_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    action: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    worker_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    details: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )


class RecoveryRecordModel(BaseModel):
    """Crash recovery tracking records."""

    __tablename__ = "recovery_records"

    execution_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    recovery_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="crash"
    )
    recovery_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )
    previous_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=""
    )
    recovered_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=""
    )
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    checkpoint_used: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class TimeoutEventModel(BaseModel):
    """Timeout event records."""

    __tablename__ = "timeout_events"

    execution_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    action: Mapped[str] = mapped_column(String(32), nullable=False, default="retry")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class DeadLetterPipelineModel(BaseModel):
    """Pipeline-level DLQ entries."""

    __tablename__ = "dead_letter_pipeline"

    dlq_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True
    )
    execution_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error_class: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    traceback: Mapped[str] = mapped_column(Text, nullable=False, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(
        SA_JSON, nullable=False, default=dict
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_history: Mapped[list[dict[str, Any]]] = mapped_column(
        SA_JSON, nullable=False, default=list
    )
    recovery_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )


class WorkflowMetricModel(BaseModel):
    """Aggregated workflow metrics."""

    __tablename__ = "workflow_metrics"

    execution_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checkpoint_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recovery_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    snapshot_size_bytes: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
