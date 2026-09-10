"""Pydantic models for the Optimization Engine."""

from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field


class OptimizationType(str, Enum):
    SEO = "seo"
    GRAMMAR = "grammar"
    READABILITY = "readability"
    HALLUCINATION = "hallucination"
    KEYWORD = "keyword"
    DUPLICATE = "duplicate"
    PASSIVE_VOICE = "passive_voice"
    FAQ = "faq"
    CTA = "cta"
    SUMMARY = "summary"
    MARKDOWN = "markdown"
    STRUCTURE = "structure"
    STYLE = "style"
    COMPLETENESS = "completeness"


class OptimizationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"


class SectionType(str, Enum):
    INTRODUCTION = "introduction"
    BODY = "body"
    TABLE = "table"
    LIST = "list"
    EXAMPLE = "example"
    FAQ = "faq"
    CONCLUSION = "conclusion"
    CTA = "cta"
    SUMMARY = "summary"
    CODE_BLOCK = "code_block"
    QUOTE = "quote"


class QualityGate(BaseModel):
    seo_min: float = Field(default=90.0, ge=0.0, le=100.0)
    grammar_min: float = Field(default=95.0, ge=0.0, le=100.0)
    readability_min: float = Field(default=90.0, ge=0.0, le=100.0)
    hallucination_max_risk: str = Field(default="low")
    markdown_valid: bool = Field(default=True)
    outline_compliant: bool = Field(default=True)


class OptimizationContext(BaseModel):
    section_text: str = Field(default="")
    section_heading: str = Field(default="")
    section_type: SectionType = Field(default=SectionType.BODY)
    outline_section: dict = Field(default_factory=dict)
    seo_plan: dict = Field(default_factory=dict)
    knowledge_graph: dict = Field(default_factory=dict)
    review_findings: list[dict] = Field(default_factory=list)
    quality_scores: dict[str, float] = Field(default_factory=dict)
    issues: list[dict] = Field(default_factory=list)
    recommendations: list[dict] = Field(default_factory=list)
    primary_keyword: str = Field(default="")
    secondary_keywords: list[str] = Field(default_factory=list)
    blog_title: str = Field(default="")
    project_id: str = Field(default="")


class OptimizationPrompt(BaseModel):
    system_prompt: str = Field(default="")
    user_prompt: str = Field(default="")
    optimization_type: OptimizationType = Field(default=OptimizationType.SEO)
    context: OptimizationContext = Field(default_factory=OptimizationContext)
    improvement_goals: list[str] = Field(default_factory=list)
    target_scores: dict[str, float] = Field(default_factory=dict)


class SectionVersion(BaseModel):
    version_id: str = Field(default="")
    section_index: int = Field(default=0)
    section_heading: str = Field(default="")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    prompt: str = Field(default="")
    content_before: str = Field(default="")
    content_after: str = Field(default="")
    scores_before: dict[str, float] = Field(default_factory=dict)
    scores_after: dict[str, float] = Field(default_factory=dict)
    optimization_type: OptimizationType = Field(default=OptimizationType.SEO)
    retry_count: int = Field(default=0)
    status: OptimizationStatus = Field(default=OptimizationStatus.PENDING)


class OptimizationResult(BaseModel):
    section_index: int = Field(default=0)
    section_heading: str = Field(default="")
    section_type: SectionType = Field(default=SectionType.BODY)
    status: OptimizationStatus = Field(default=OptimizationStatus.PENDING)
    content_before: str = Field(default="")
    content_after: str = Field(default="")
    scores_before: dict[str, float] = Field(default_factory=dict)
    scores_after: dict[str, float] = Field(default_factory=dict)
    optimization_types: list[OptimizationType] = Field(default_factory=list)
    retries_used: int = Field(default=0)
    retry_history: list[SectionVersion] = Field(default_factory=list)
    rolled_back: bool = Field(default=False)
    rollback_reason: str = Field(default="")
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    execution_time_ms: float = Field(default=0.0)
    cached: bool = Field(default=False)


class OptimizationPlan(BaseModel):
    section_index: int = Field(default=0)
    section_heading: str = Field(default="")
    section_type: SectionType = Field(default=SectionType.BODY)
    optimization_types: list[OptimizationType] = Field(default_factory=list)
    priority: int = Field(default=0)
    quality_scores: dict[str, float] = Field(default_factory=dict)
    issues: list[dict] = Field(default_factory=list)
    needs_optimization: bool = Field(default=False)
    reason: str = Field(default="")


class OptimizationReport(BaseModel):
    project_id: str = Field(default="")
    blog_title: str = Field(default="")
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    execution_time_ms: float = Field(default=0.0)
    total_sections: int = Field(default=0)
    sections_optimized: int = Field(default=0)
    sections_skipped: int = Field(default=0)
    sections_failed: int = Field(default=0)
    sections_rolled_back: int = Field(default=0)
    total_retries: int = Field(default=0)
    results: list[OptimizationResult] = Field(default_factory=list)
    overall_improvement: dict[str, float] = Field(default_factory=dict)
    quality_gates_passed: bool = Field(default=False)
    remaining_issues: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    version_history: list[SectionVersion] = Field(default_factory=list)


class OptimizationConfig(BaseModel):
    max_retries: int = Field(default=3, ge=0, le=10)
    quality_gates: QualityGate = Field(default_factory=QualityGate)
    parallel_sections: bool = Field(default=False)
    cache_enabled: bool = Field(default=True)
    checkpoint_enabled: bool = Field(default=True)
    output_dir: str = Field(default="output")
    log_level: str = Field(default="INFO")
    model: str = Field(default="gpt-4")
    temperature: float = Field(default=0.3)
    max_tokens: int = Field(default=2048)


class OptimizedSection(BaseModel):
    section_index: int = Field(default=0)
    heading: str = Field(default="")
    original_content: str = Field(default="")
    optimized_content: str = Field(default="")
    optimization_types: list[OptimizationType] = Field(default_factory=list)
    scores_before: dict[str, float] = Field(default_factory=dict)
    scores_after: dict[str, float] = Field(default_factory=dict)
    status: OptimizationStatus = Field(default=OptimizationStatus.PENDING)


class OptimizedDraft(BaseModel):
    project_id: str = Field(default="")
    title: str = Field(default="")
    sections: list[OptimizedSection] = Field(default_factory=list)
    full_content: str = Field(default="")
    metadata: dict = Field(default_factory=dict)
