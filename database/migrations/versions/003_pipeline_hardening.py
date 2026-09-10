"""Production Pipeline Hardening — 12 new tables for durable workflow orchestration.

Revision ID: 003_pipeline_hardening
Revises: 002_transcript_reliability
Create Date: 2026-07-07
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_pipeline_hardening"
down_revision: str | None = "002_transcript_reliability"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # workflow_executions
    op.create_table(
        "workflow_executions",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("execution_id", sa.String(36), nullable=False, unique=True, index=True),
        sa.Column("project_id", sa.String(36), nullable=False, index=True),
        sa.Column("video_id", sa.String(64), nullable=False, server_default="", index=True),
        sa.Column("workflow_state", sa.String(32), nullable=False, server_default="created"),
        sa.Column("current_stage", sa.String(64), nullable=False, server_default=""),
        sa.Column("completed_stages", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("failed_stages", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recovery_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_duration_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("correlation_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("trace_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("worker_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("extra_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("uuid"),
    )

    # workflow_stages
    op.create_table(
        "workflow_stages",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("stage_id", sa.String(36), nullable=False, unique=True, index=True),
        sa.Column("execution_id", sa.String(36), nullable=False, index=True),
        sa.Column("stage_name", sa.String(64), nullable=False, index=True),
        sa.Column("state", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("input_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("output_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("error_class", sa.String(32), nullable=False, server_default=""),
        sa.Column("checkpoint_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("snapshot_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("worker_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("provider", sa.String(64), nullable=False, server_default=""),
        sa.Column("model", sa.String(64), nullable=False, server_default=""),
        sa.Column("extra_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("uuid"),
    )

    # pipeline_checkpoints
    op.create_table(
        "pipeline_checkpoints",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("checkpoint_id", sa.String(36), nullable=False, unique=True, index=True),
        sa.Column("execution_id", sa.String(36), nullable=False, index=True),
        sa.Column("stage_name", sa.String(64), nullable=False, index=True),
        sa.Column("stage_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default=""),
        sa.Column("input_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("output_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("input_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("output_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("uuid"),
    )

    # stage_snapshots
    op.create_table(
        "stage_snapshots",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("snapshot_id", sa.String(36), nullable=False, unique=True, index=True),
        sa.Column("execution_id", sa.String(36), nullable=False, index=True),
        sa.Column("stage_name", sa.String(64), nullable=False, index=True),
        sa.Column("content_hash", sa.String(64), nullable=False, index=True),
        sa.Column("inputs", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("outputs", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("model", sa.String(64), nullable=False, server_default=""),
        sa.Column("provider", sa.String(64), nullable=False, server_default=""),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("generated_files", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("metrics", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("logs", sa.JSON(), nullable=False, server_default="[]"),
        sa.PrimaryKeyConstraint("uuid"),
    )

    # idempotency_keys
    op.create_table(
        "idempotency_keys",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("key", sa.String(128), nullable=False, unique=True, index=True),
        sa.Column("execution_id", sa.String(36), nullable=False, index=True),
        sa.Column("stage_name", sa.String(64), nullable=False, server_default=""),
        sa.Column("input_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("output_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("status", sa.String(32), nullable=False, server_default="completed"),
        sa.Column("expires_at", sa.String(32), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("uuid"),
    )

    # execution_history
    op.create_table(
        "execution_history",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("event_id", sa.String(36), nullable=False, unique=True, index=True),
        sa.Column("execution_id", sa.String(36), nullable=False, index=True),
        sa.Column("stage_name", sa.String(64), nullable=False, server_default=""),
        sa.Column("action", sa.String(64), nullable=False, server_default=""),
        sa.Column("status", sa.String(32), nullable=False, server_default=""),
        sa.Column("request_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("correlation_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("trace_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("worker_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("uuid"),
    )

    # recovery_records
    op.create_table(
        "recovery_records",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("execution_id", sa.String(36), nullable=False, index=True),
        sa.Column("recovery_type", sa.String(32), nullable=False, server_default="crash"),
        sa.Column("recovery_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("previous_state", sa.String(32), nullable=False, server_default=""),
        sa.Column("recovered_state", sa.String(32), nullable=False, server_default=""),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("checkpoint_used", sa.String(36), nullable=False, server_default=""),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("uuid"),
    )

    # timeout_events
    op.create_table(
        "timeout_events",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("execution_id", sa.String(36), nullable=False, index=True),
        sa.Column("stage_name", sa.String(64), nullable=False, server_default=""),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("action", sa.String(32), nullable=False, server_default="retry"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("uuid"),
    )

    # dead_letter_pipeline
    op.create_table(
        "dead_letter_pipeline",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("dlq_id", sa.String(36), nullable=False, unique=True, index=True),
        sa.Column("execution_id", sa.String(36), nullable=False, index=True),
        sa.Column("project_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("stage_name", sa.String(64), nullable=False, server_default=""),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("error_class", sa.String(32), nullable=False, server_default=""),
        sa.Column("traceback", sa.Text(), nullable=False, server_default=""),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_history", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("recovery_status", sa.String(32), nullable=False, server_default="pending"),
        sa.PrimaryKeyConstraint("uuid"),
    )

    # workflow_metrics
    op.create_table(
        "workflow_metrics",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("execution_id", sa.String(36), nullable=False, index=True),
        sa.Column("stage_name", sa.String(64), nullable=False, server_default=""),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checkpoint_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recovery_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("snapshot_size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("uuid"),
    )


def downgrade() -> None:
    op.drop_table("workflow_metrics")
    op.drop_table("dead_letter_pipeline")
    op.drop_table("timeout_events")
    op.drop_table("recovery_records")
    op.drop_table("execution_history")
    op.drop_table("idempotency_keys")
    op.drop_table("stage_snapshots")
    op.drop_table("pipeline_checkpoints")
    op.drop_table("workflow_stages")
    op.drop_table("workflow_executions")
