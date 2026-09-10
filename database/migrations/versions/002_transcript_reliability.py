"""Transcript Reliability Engine — 10 new tables for enterprise-grade transcript management.

Revision ID: 002_transcript_reliability
Revises: 55bc52dfc0c9
Create Date: 2026-07-07
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002_transcript_reliability"
down_revision: str | None = "55bc52dfc0c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### transcript_providers ###
    op.create_table(
        "transcript_providers",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("provider_id", sa.String(64), nullable=False, index=True, unique=True),
        sa.Column("name", sa.String(128), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("capabilities", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("cost_per_minute", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("supported_languages", sa.JSON(), nullable=False, server_default="[]"),
        sa.PrimaryKeyConstraint("uuid"),
    )

    # ### provider_health ###
    op.create_table(
        "provider_health",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("provider_id", sa.String(64), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("availability", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("success_rate", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("avg_latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("p95_latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("p99_latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quota_usage", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("last_error", sa.Text(), nullable=False, server_default=""),
        sa.Column("last_error_at", sa.String(32), nullable=False, server_default=""),
        sa.Column("last_success_at", sa.String(32), nullable=False, server_default=""),
        sa.Column("recent_errors", sa.JSON(), nullable=False, server_default="[]"),
        sa.PrimaryKeyConstraint("uuid"),
    )

    # ### transcript_versions ###
    op.create_table(
        "transcript_versions",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("transcript_id", sa.String(36), nullable=False, index=True),
        sa.Column("video_id", sa.String(64), nullable=False, index=True),
        sa.Column("version_type", sa.String(32), nullable=False, server_default="current"),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("content_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("plain_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("language", sa.String(16), nullable=False, server_default="en"),
        sa.Column("source", sa.String(64), nullable=False, server_default=""),
        sa.Column("parent_version_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("change_reason", sa.String(255), nullable=False, server_default=""),
        sa.Column("version_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("uuid"),
    )

    # ### transcript_cache ###
    op.create_table(
        "transcript_cache",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("cache_key", sa.String(128), nullable=False, index=True, unique=True),
        sa.Column("video_id", sa.String(64), nullable=False, index=True),
        sa.Column("language", sa.String(16), nullable=False, server_default="en"),
        sa.Column("provider_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("version_type", sa.String(32), nullable=False, server_default="current"),
        sa.Column("data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("expires_at", sa.String(32), nullable=False, server_default=""),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("uuid"),
    )

    # ### transcript_validations ###
    op.create_table(
        "transcript_validations",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("transcript_id", sa.String(36), nullable=False, index=True),
        sa.Column("video_id", sa.String(64), nullable=False, index=True),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("checks", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("failed_checks", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("errors", sa.JSON(), nullable=False, server_default="[]"),
        sa.PrimaryKeyConstraint("uuid"),
    )

    # ### transcript_quality ###
    op.create_table(
        "transcript_quality",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("transcript_id", sa.String(36), nullable=False, index=True),
        sa.Column("video_id", sa.String(64), nullable=False, index=True),
        sa.Column("overall", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("grade", sa.String(16), nullable=False, server_default="fair"),
        sa.Column("dimensions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("provider_reliability_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.PrimaryKeyConstraint("uuid"),
    )

    # ### transcript_metrics ###
    op.create_table(
        "transcript_metrics",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("video_id", sa.String(64), nullable=False, index=True),
        sa.Column("total_duration_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("cache_level", sa.String(16), nullable=False, server_default=""),
        sa.Column("provider_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("provider_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fallback_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("validation_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("language", sa.String(16), nullable=False, server_default=""),
        sa.Column("circuit_breaker_events", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("errors", sa.JSON(), nullable=False, server_default="[]"),
        sa.PrimaryKeyConstraint("uuid"),
    )

    # ### transcript_failures ###
    op.create_table(
        "transcript_failures",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("video_id", sa.String(64), nullable=False, index=True),
        sa.Column("provider_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("error_type", sa.String(64), nullable=False, server_default=""),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fallback_chain", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("circuit_breaker_state", sa.String(16), nullable=False, server_default="closed"),
        sa.Column("recoverable", sa.Boolean(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("uuid"),
    )

    # ### transcript_retries ###
    op.create_table(
        "transcript_retries",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("video_id", sa.String(64), nullable=False, index=True),
        sa.Column("provider_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("delay_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("decision", sa.String(16), nullable=False, server_default="retry"),
        sa.PrimaryKeyConstraint("uuid"),
    )

    # ### provider_statistics ###
    op.create_table(
        "provider_statistics",
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False, index=True),
        sa.Column("provider_id", sa.String(64), nullable=False, index=True),
        sa.Column("total_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("avg_latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("p95_latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("p99_latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("quota_consumed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_incurred", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("window_start", sa.String(32), nullable=False, server_default=""),
        sa.Column("window_end", sa.String(32), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("uuid"),
    )


def downgrade() -> None:
    op.drop_table("provider_statistics")
    op.drop_table("transcript_retries")
    op.drop_table("transcript_failures")
    op.drop_table("transcript_metrics")
    op.drop_table("transcript_quality")
    op.drop_table("transcript_validations")
    op.drop_table("transcript_cache")
    op.drop_table("transcript_versions")
    op.drop_table("provider_health")
    op.drop_table("transcript_providers")
