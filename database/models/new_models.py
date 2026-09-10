"""Additional database models — NEW tables only, no conflicts with existing.

Adds: channels, transcript_segments, transcript_translations, knowledge_nodes,
knowledge_edges, keywords, pipeline_runs, pipeline_stages, project_settings,
users, organizations, roles, permissions, jobs, notifications, etc.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import BaseModel, db_json, utcnow


class ChannelModel(BaseModel):
    __tablename__ = "channels"

    channel_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    handle: Mapped[str] = mapped_column(String(100), nullable=True)
    thumbnail_url: Mapped[str] = mapped_column(String(500), nullable=True)
    subscriber_count: Mapped[int] = mapped_column(Integer, nullable=True)
    video_count: Mapped[int] = mapped_column(Integer, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)


class TranscriptSegmentModel(BaseModel):
    __tablename__ = "transcript_segments"

    transcript_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("transcripts.uuid", ondelete="CASCADE"),
        nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class TranscriptTranslationModel(BaseModel):
    __tablename__ = "transcript_translations"
    __table_args__ = (
        UniqueConstraint("transcript_uuid", "target_language", name="uq_transl_tr_lang"),
    )

    transcript_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("transcripts.uuid", ondelete="CASCADE"),
        nullable=False, index=True
    )
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)


class KnowledgeNodeModel(BaseModel):
    __tablename__ = "knowledge_nodes"

    kg_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_graphs.uuid", ondelete="CASCADE"),
        nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    importance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)


class KnowledgeEdgeModel(BaseModel):
    __tablename__ = "knowledge_edges"

    kg_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_graphs.uuid", ondelete="CASCADE"),
        nullable=False, index=True
    )
    source_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_nodes.uuid", ondelete="CASCADE"),
        nullable=False, index=True
    )
    target_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_nodes.uuid", ondelete="CASCADE"),
        nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)


class KeywordModel(BaseModel):
    __tablename__ = "keywords"
    __table_args__ = (
        UniqueConstraint("keyword", name="uq_keyword"),
    )

    keyword: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    search_volume: Mapped[int] = mapped_column(Integer, nullable=True)
    difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpc: Mapped[float | None] = mapped_column(Float, nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)


class PipelineRunModel(BaseModel):
    __tablename__ = "pipeline_runs"

    project_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.uuid", ondelete="CASCADE"),
        nullable=False, index=True
    )
    pipeline_version: Mapped[str] = mapped_column(String(20), default="3.0", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    trigger: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)


class PipelineStageModel(BaseModel):
    __tablename__ = "pipeline_stages"

    run_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipeline_runs.uuid", ondelete="CASCADE"),
        nullable=False, index=True
    )
    stage_name: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_data: Mapped[dict | None] = mapped_column(db_json, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)


class ProjectSettingModel(BaseModel):
    __tablename__ = "project_settings"
    __table_args__ = (
        UniqueConstraint("project_uuid", "key", name="uq_proj_setting"),
    )

    project_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.uuid", ondelete="CASCADE"),
        nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[dict] = mapped_column(db_json, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)


class DraftSectionModel(BaseModel):
    __tablename__ = "draft_sections"

    draft_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("drafts.uuid", ondelete="CASCADE"),
        nullable=False, index=True
    )
    heading: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)


class PublishingHistoryModel(BaseModel):
    __tablename__ = "publishing_history"

    project_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.uuid", ondelete="CASCADE"),
        nullable=False, index=True
    )
    draft_uuid: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("drafts.uuid", ondelete="SET NULL"),
        nullable=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    published_url: Mapped[str] = mapped_column(String(500), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)


class UserModel(BaseModel):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=True)
    avatar_url: Mapped[str] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locale: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)


class OrganizationModel(BaseModel):
    __tablename__ = "organizations"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_org_slug"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str] = mapped_column(String(500), nullable=True)
    owner_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.uuid", ondelete="CASCADE"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tier: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    max_members: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_projects: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)


class OrganizationMemberModel(BaseModel):
    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("organization_uuid", "user_uuid", name="uq_org_member"),
    )

    organization_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.uuid", ondelete="CASCADE"),
        nullable=False, index=True
    )
    user_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.uuid", ondelete="CASCADE"),
        nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(50), default="member", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class JobModel(BaseModel):
    __tablename__ = "jobs"

    project_uuid: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("projects.uuid", ondelete="SET NULL"),
        nullable=True, index=True
    )
    job_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    queue_name: Mapped[str] = mapped_column(String(50), default="default", nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)
    result_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    celery_task_id: Mapped[str] = mapped_column(String(255), nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)


class JobExecutionModel(BaseModel):
    __tablename__ = "job_executions"

    job_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.uuid", ondelete="CASCADE"),
        nullable=False, index=True
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False)
    worker_id: Mapped[str] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    output_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)


class NotificationModel(BaseModel):
    __tablename__ = "notifications"

    user_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.uuid", ondelete="CASCADE"),
        nullable=False, index=True
    )
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=True)
    data_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    channel: Mapped[str] = mapped_column(String(50), default="in_app", nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NotificationTemplateModel(BaseModel):
    __tablename__ = "notification_templates"
    __table_args__ = (
        UniqueConstraint("notification_type", "channel", name="uq_notif_tmpl"),
    )

    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    title_template: Mapped[str] = mapped_column(String(500), nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    variables_json: Mapped[list] = mapped_column(db_json, default=list, nullable=False)


class WebhookModel(BaseModel):
    __tablename__ = "webhooks"
    __table_args__ = (
        UniqueConstraint("name", name="uq_webhook_name"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    events: Mapped[list] = mapped_column(db_json, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WebhookDeliveryModel(BaseModel):
    __tablename__ = "webhook_deliveries"

    webhook_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("webhooks.uuid", ondelete="CASCADE"),
        nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    request_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FeatureFlagModel(BaseModel):
    __tablename__ = "feature_flags"

    flag_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    config_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=True)


class SystemLogModel(BaseModel):
    __tablename__ = "system_logs"

    level: Mapped[str] = mapped_column(String(20), default="info", nullable=False, index=True)
    logger: Mapped[str] = mapped_column(String(100), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    module: Mapped[str] = mapped_column(String(100), nullable=True)
    function: Mapped[str] = mapped_column(String(100), nullable=True)
    line: Mapped[int] = mapped_column(Integer, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)


class PlanModel(BaseModel):
    __tablename__ = "plans"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_plan_slug"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="usd", nullable=False)
    interval: Mapped[str] = mapped_column(String(20), default="month", nullable=False)
    trial_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    features_json: Mapped[dict] = mapped_column(db_json, nullable=False)
    limits_json: Mapped[dict] = mapped_column(db_json, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stripe_price_id: Mapped[str] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)


class SubscriptionModel(BaseModel):
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("organization_uuid", "stripe_subscription_id", name="uq_sub_stripe"),
    )

    organization_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.uuid", ondelete="CASCADE"),
        nullable=False, index=True
    )
    plan_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("plans.uuid", ondelete="RESTRICT"),
        nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False, index=True)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)


class UsageTrackingModel(BaseModel):
    __tablename__ = "usage_tracking"

    organization_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.uuid", ondelete="CASCADE"),
        nullable=False, index=True
    )
    user_uuid: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.uuid", ondelete="SET NULL"),
        nullable=True
    )
    metric: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(db_json, nullable=True)
