from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PromptStatus(str, Enum):
    draft = "draft"
    review = "review"
    approved = "approved"
    production = "production"
    deprecated = "deprecated"
    archived = "archived"
    rejected = "rejected"


class PromptCategory(str, Enum):
    analysis = "analysis"
    knowledge_graph = "knowledge_graph"
    seo = "seo"
    outline = "outline"
    section = "section"
    review = "review"
    rewrite = "rewrite"
    optimization = "optimization"
    translation = "translation"
    faq = "faq"
    cta = "cta"
    summary = "summary"
    system = "system"
    shared = "shared"
    custom = "custom"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class DeploymentStatus(str, Enum):
    draft = "draft"
    staging = "staging"
    production = "production"
    rolled_back = "rolled_back"


class ExperimentStatus(str, Enum):
    draft = "draft"
    running = "running"
    completed = "completed"
    cancelled = "cancelled"
    promoting = "promoting"


class PromptMetadata(BaseModel):
    prompt_id: str = Field(default_factory=lambda: f"p_{uuid.uuid4().hex[:12]}")
    name: str
    version: str = "1.0.0"
    author: str = "system"
    status: PromptStatus = PromptStatus.draft
    category: PromptCategory = PromptCategory.custom
    tags: list[str] = Field(default_factory=list)
    language: str = "en"
    target_model: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096
    owner: str = ""
    approval: str = "pending"
    risk_level: RiskLevel = RiskLevel.low
    supported_models: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    description: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_updated_by: str = ""
    change_log: list[dict[str, Any]] = Field(default_factory=list)
    source_file: str = ""
    content_hash: str = ""

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            msg = f"Version must be semver (X.Y.Z), got: {v}"
            raise ValueError(msg)
        return v


class PromptVersion(BaseModel):
    version_id: str = Field(default_factory=lambda: f"pv_{uuid.uuid4().hex[:12]}")
    prompt_id: str
    version_number: str
    previous_version: str | None = None
    content: str
    author: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    change_summary: str = ""
    changes: list[dict[str, Any]] = Field(default_factory=list)
    diff: str = ""
    approved_by: str = ""
    approval_date: str = ""
    linked_ticket: str = ""
    release_version: str = ""
    status: PromptStatus = PromptStatus.draft
    content_hash: str = ""


class PromptAnalytics(BaseModel):
    analytics_id: str = Field(default_factory=lambda: f"pa_{uuid.uuid4().hex[:12]}")
    prompt_id: str
    version: str
    execution_count: int = 0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    failure_count: int = 0
    success_count: int = 0
    success_rate: float = 1.0
    avg_quality_score: float = 0.0
    model_used: str = ""
    last_executed: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExperimentVariant(BaseModel):
    variant_id: str = Field(default_factory=lambda: f"ev_{uuid.uuid4().hex[:8]}")
    name: str
    prompt_id: str
    version: str
    traffic_percent: float = 50.0
    is_control: bool = False
    config_overrides: dict[str, Any] = Field(default_factory=dict)


class ExperimentResult(BaseModel):
    variant_id: str
    executions: int = 0
    successes: int = 0
    failures: int = 0
    avg_latency_ms: float = 0.0
    avg_quality_score: float = 0.0
    avg_tokens: float = 0.0
    total_cost: float = 0.0


class PromptExperiment(BaseModel):
    experiment_id: str = Field(default_factory=lambda: f"pe_{uuid.uuid4().hex[:12]}")
    name: str
    description: str = ""
    status: ExperimentStatus = ExperimentStatus.draft
    variants: list[ExperimentVariant] = Field(default_factory=list)
    results: dict[str, ExperimentResult] = Field(default_factory=dict)
    winner_variant_id: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: str = ""
    target_prompt_id: str = ""
    min_executions: int = 100
    confidence_threshold: float = 0.95
    promotion_trigger: str = "manual"
