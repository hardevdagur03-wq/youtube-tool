"""Pydantic models for the Section Generation Engine.

Every section is an independent unit with its own metadata, version,
validation, and output. No section depends on another's context window.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SectionType(str, Enum):
    INTRODUCTION = "introduction"
    PROBLEM = "problem"
    EXPLANATION = "explanation"
    STEP_BY_STEP = "step_by_step"
    COMPARISON = "comparison"
    DEFINITION = "definition"
    BENEFITS = "benefits"
    DRAWBACKS = "drawbacks"
    USE_CASES = "use_cases"
    EXAMPLES = "examples"
    CASE_STUDIES = "case_studies"
    TABLE = "table"
    LIST = "list"
    CODE = "code"
    QUOTE = "quote"
    FAQ = "faq"
    SUMMARY = "summary"
    CONCLUSION = "conclusion"
    CTA = "cta"
    BODY = "body"


class SectionStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CACHED = "cached"


class GenerationResult(BaseModel):
    success: bool = False
    content: str = ""
    error: str = ""
    warnings: list[str] = Field(default_factory=list)
    tokens_used: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: float = 0.0
    cost_estimate: float = 0.0
    retry_count: int = 0
    cache_hit: bool = False


class SectionPrompt(BaseModel):
    system_prompt: str = ""
    user_prompt: str = ""
    template_version: str = "1.0.0"
    prompt_tokens_estimate: int = 0


class SectionContext(BaseModel):
    section_id: str = ""
    section_type: SectionType = SectionType.BODY
    heading: str = ""
    goal: str = ""
    order: int = 0
    target_word_count: int = 250

    keywords: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    statistics: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    solutions: list[str] = Field(default_factory=list)
    definitions: list[dict[str, str]] = Field(default_factory=list)
    quotes: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    key_concepts: list[str] = Field(default_factory=list)
    supporting_facts: list[str] = Field(default_factory=list)

    internal_links: list[str] = Field(default_factory=list)
    external_links: list[str] = Field(default_factory=list)

    primary_keyword: str = ""
    search_intent: str = "informational"
    target_audience: str = ""
    tone: str = "conversational"
    writing_style: str = "standard"
    brand_voice: str = "professional"

    content_angle: str = ""
    unique_value: str = ""

    dependencies: list[str] = Field(default_factory=list)
    depends_on_sections: list[str] = Field(default_factory=list)

    metadata: dict[str, Any] = Field(default_factory=dict)


class SectionOutput(BaseModel):
    section_id: str = ""
    section_type: SectionType = SectionType.BODY
    heading: str = ""
    content: str = ""
    order: int = 0
    word_count: int = 0
    reading_time_seconds: int = 0

    keywords_used: list[str] = Field(default_factory=list)
    entities_used: list[str] = Field(default_factory=list)
    facts_used: list[str] = Field(default_factory=list)
    internal_links_used: list[str] = Field(default_factory=list)
    external_links_used: list[str] = Field(default_factory=list)

    version: int = 1
    generation_time_ms: float = 0.0
    tokens_input: int = 0
    tokens_output: int = 0
    cost_estimate: float = 0.0
    retry_count: int = 0
    cache_hit: bool = False
    status: SectionStatus = SectionStatus.PENDING

    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class SectionVersion(BaseModel):
    version_number: int = 1
    created_at: str = ""
    content_hash: str = ""
    content: str = ""
    prompt: str = ""
    validation_score: float = 0.0
    generation_time_ms: float = 0.0
    tokens_used: int = 0
    reason: str = ""


class SectionValidation(BaseModel):
    section_id: str = ""
    validated_at: str = ""
    valid: bool = False
    score: float = 0.0

    grammar_score: float = 0.0
    seo_coverage_score: float = 0.0
    keyword_usage_score: float = 0.0
    heading_alignment_score: float = 0.0
    word_count_valid: bool = False
    fact_consistency_score: float = 0.0
    outline_compliance_score: float = 0.0
    duplicate_content_score: float = 0.0
    readability_score: float = 0.0
    hallucination_risk_score: float = 0.0

    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SectionMetadata(BaseModel):
    section_id: str = ""
    section_type: SectionType = SectionType.BODY
    heading: str = ""
    order: int = 0
    word_count: int = 0
    reading_time_seconds: int = 0
    keywords_used: list[str] = Field(default_factory=list)
    entities_used: list[str] = Field(default_factory=list)
    facts_used: list[str] = Field(default_factory=list)
    version: int = 1
    generation_time_ms: float = 0.0
    validation_score: float = 0.0
    status: SectionStatus = SectionStatus.PENDING
    created_at: str = ""
    updated_at: str = ""


class SectionManifest(BaseModel):
    project_id: str = ""
    total_sections: int = 0
    completed_sections: int = 0
    failed_sections: int = 0
    pending_sections: int = 0
    overall_progress_pct: float = 0.0
    sections: dict[str, SectionMetadata] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


class GenerationConfig(BaseModel):
    max_retries: int = 3
    base_delay: float = 2.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 120
    enable_cache: bool = True
    enable_validation: bool = True
    enable_versioning: bool = True
    parallel_generation: bool = False
    fail_fast: bool = False
    provider: str = ""
    model: str = ""


class ProgressReport(BaseModel):
    current_section: str = ""
    current_index: int = 0
    total_sections: int = 0
    completed: int = 0
    failed: int = 0
    pending: int = 0
    progress_pct: float = 0.0
    elapsed_seconds: float = 0.0
    estimated_remaining_seconds: float = 0.0
    avg_section_time_ms: float = 0.0
    total_tokens_used: int = 0
    total_cost: float = 0.0
    cache_hits: int = 0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_section_id(section_type: SectionType, order: int = 0) -> str:
    prefix = {
        SectionType.INTRODUCTION: "intro",
        SectionType.PROBLEM: "problem",
        SectionType.EXPLANATION: "expl",
        SectionType.STEP_BY_STEP: "steps",
        SectionType.COMPARISON: "compare",
        SectionType.DEFINITION: "define",
        SectionType.BENEFITS: "benefits",
        SectionType.DRAWBACKS: "drawbacks",
        SectionType.USE_CASES: "usecases",
        SectionType.EXAMPLES: "examples",
        SectionType.CASE_STUDIES: "casestudy",
        SectionType.TABLE: "table",
        SectionType.LIST: "list",
        SectionType.CODE: "code",
        SectionType.QUOTE: "quote",
        SectionType.FAQ: "faq",
        SectionType.SUMMARY: "summary",
        SectionType.CONCLUSION: "conclusion",
        SectionType.CTA: "cta",
        SectionType.BODY: "section",
    }
    p = prefix.get(section_type, "section")
    return f"{p}_{order:02d}" if order > 0 else p


def estimate_reading_time_seconds(word_count: int) -> int:
    return max(1, round(word_count / 200 * 60))
