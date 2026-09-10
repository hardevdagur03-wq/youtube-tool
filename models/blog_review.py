"""Pydantic models for Phase 9 — AI Blog Review & Quality Assurance Engine."""

from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field


class IssueSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class HallucinationRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PublishDecision(str, Enum):
    ENTERPRISE_READY = "enterprise_ready"
    PUBLISH_READY = "publish_ready"
    MINOR_REVISIONS = "minor_revisions"
    MAJOR_REVISIONS = "major_revisions"
    REJECT = "reject"


class ReviewIssue(BaseModel):
    description: str
    location: str = Field(default="", description="Section or element where issue was found")
    severity: IssueSeverity
    why_it_matters: str = Field(default="")
    recommended_fix: str = Field(default="")


class GrammarResult(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    issues: list[ReviewIssue] = Field(default_factory=list)
    spelling_errors: int = Field(default=0)
    grammar_errors: int = Field(default=0)
    punctuation_errors: int = Field(default=0)
    passive_voice_sentences: int = Field(default=0)
    run_on_sentences: int = Field(default=0)
    sentence_fragments: int = Field(default=0)


class ReadabilityResult(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    flesch_reading_ease: float = Field(default=0.0)
    flesch_kincaid_grade: float = Field(default=0.0)
    avg_sentence_length: float = Field(default=0.0)
    avg_paragraph_length: float = Field(default=0.0)
    complex_sentence_ratio: float = Field(default=0.0)
    transition_word_ratio: float = Field(default=0.0)
    passive_voice_percentage: float = Field(default=0.0)
    reading_time_minutes: float = Field(default=0.0)
    difficulty_level: str = Field(default="")
    improvement_suggestions: list[str] = Field(default_factory=list)


class SEOResult(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    title_length: int = Field(default=0)
    meta_title_length: int = Field(default=0)
    meta_description_length: int = Field(default=0)
    primary_keyword_in_title: bool = Field(default=False)
    primary_keyword_in_meta_title: bool = Field(default=False)
    primary_keyword_in_meta_description: bool = Field(default=False)
    primary_keyword_in_introduction: bool = Field(default=False)
    primary_keyword_in_h1: bool = Field(default=False)
    primary_keyword_in_h2: bool = Field(default=False)
    primary_keyword_in_conclusion: bool = Field(default=False)
    keyword_stuffing_detected: bool = Field(default=False)
    missing_elements: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class DuplicateResult(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    duplicate_paragraphs: int = Field(default=0)
    duplicate_headings: int = Field(default=0)
    repeated_sections: list[str] = Field(default_factory=list)
    merge_recommendations: list[str] = Field(default_factory=list)


class HeadingResult(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    h1_count: int = Field(default=0)
    hierarchy_issues: list[str] = Field(default_factory=list)
    missing_headings: list[str] = Field(default_factory=list)
    skipped_levels: list[str] = Field(default_factory=list)


class CompletenessResult(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    has_introduction: bool = Field(default=False)
    has_core_explanation: bool = Field(default=False)
    has_examples: bool = Field(default=False)
    has_best_practices: bool = Field(default=False)
    has_benefits: bool = Field(default=False)
    has_limitations: bool = Field(default=False)
    has_faq: bool = Field(default=False)
    has_summary: bool = Field(default=False)
    has_call_to_action: bool = Field(default=False)
    missing_sections: list[str] = Field(default_factory=list)
    suggested_topics: list[str] = Field(default_factory=list)


class HallucinationResult(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    risk_level: HallucinationRisk = Field(default=HallucinationRisk.LOW)
    flagged_statements: list[dict] = Field(default_factory=list)
    unsupported_claims: int = Field(default=0)
    unverifiable_statistics: int = Field(default=0)
    fabricated_references: int = Field(default=0)
    recommendations: list[str] = Field(default_factory=list)


class FactConsistencyResult(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    conflicting_statements: list[str] = Field(default_factory=list)
    timeline_inconsistencies: list[str] = Field(default_factory=list)
    number_inconsistencies: list[str] = Field(default_factory=list)


class EEATResult(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    experience_score: float = Field(default=0.0, ge=0.0, le=100.0)
    expertise_score: float = Field(default=0.0, ge=0.0, le=100.0)
    authoritativeness_score: float = Field(default=0.0, ge=0.0, le=100.0)
    trustworthiness_score: float = Field(default=0.0, ge=0.0, le=100.0)
    weak_areas: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class LinkingResult(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    internal_link_count: int = Field(default=0)
    external_link_count: int = Field(default=0)
    broken_links: list[str] = Field(default_factory=list)
    poor_anchor_text: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class AccessibilityResult(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    images_missing_alt: int = Field(default=0)
    heading_structure_issues: list[str] = Field(default_factory=list)
    link_text_issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ContentQualityResult(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    clarity_score: float = Field(default=0.0, ge=0.0, le=100.0)
    logical_flow_score: float = Field(default=0.0, ge=0.0, le=100.0)
    actionability_score: float = Field(default=0.0, ge=0.0, le=100.0)
    originality_score: float = Field(default=0.0, ge=0.0, le=100.0)
    engagement_score: float = Field(default=0.0, ge=0.0, le=100.0)
    tone_consistency_score: float = Field(default=0.0, ge=0.0, le=100.0)
    issues: list[ReviewIssue] = Field(default_factory=list)


class AIDetectionResult(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    risk_level: str = Field(default="low")
    repetitive_phrases: list[str] = Field(default_factory=list)
    lexical_diversity_score: float = Field(default=0.0)
    avg_sentence_length_variety: float = Field(default=0.0)
    recommendations: list[str] = Field(default_factory=list)


class CategoryScore(BaseModel):
    category: str
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    weight: float = Field(default=0.0, ge=0.0, le=1.0)
    status: str = Field(default="")


class Scorecard(BaseModel):
    categories: list[CategoryScore] = Field(default_factory=list)
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0)


class QualityReport(BaseModel):
    # Metadata
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    execution_time_ms: float = Field(default=0.0)

    # Input
    blog_title: str = Field(default="")
    word_count: int = Field(default=0)
    estimated_reading_time: str = Field(default="")

    # Executive summary
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0)
    publish_decision: PublishDecision = Field(default=PublishDecision.REJECT)
    executive_summary: str = Field(default="")

    # Detailed results
    grammar: GrammarResult = Field(default_factory=GrammarResult)
    readability: ReadabilityResult = Field(default_factory=ReadabilityResult)
    seo: SEOResult = Field(default_factory=SEOResult)
    duplicate: DuplicateResult = Field(default_factory=DuplicateResult)
    headings: HeadingResult = Field(default_factory=HeadingResult)
    completeness: CompletenessResult = Field(default_factory=CompletenessResult)
    hallucination: HallucinationResult = Field(default_factory=HallucinationResult)
    fact_consistency: FactConsistencyResult = Field(default_factory=FactConsistencyResult)
    eeat: EEATResult = Field(default_factory=EEATResult)
    internal_linking: LinkingResult = Field(default_factory=LinkingResult)
    external_linking: LinkingResult = Field(default_factory=LinkingResult)
    accessibility: AccessibilityResult = Field(default_factory=AccessibilityResult)
    content_quality: ContentQualityResult = Field(default_factory=ContentQualityResult)
    ai_detection: AIDetectionResult = Field(default_factory=AIDetectionResult)

    # Aggregated
    scorecard: Scorecard = Field(default_factory=Scorecard)
    all_issues: list[ReviewIssue] = Field(default_factory=list)
    critical_issues: list[ReviewIssue] = Field(default_factory=list)
    high_issues: list[ReviewIssue] = Field(default_factory=list)
    medium_issues: list[ReviewIssue] = Field(default_factory=list)
    low_issues: list[ReviewIssue] = Field(default_factory=list)

    # Recommendations
    must_fix: list[str] = Field(default_factory=list)
    should_improve: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)

    # Markdown report
    markdown: str = Field(default="")


class BlogReviewRequest(BaseModel):
    blog_title: str = Field(default="")
    primary_keyword: str = Field(default="")
    secondary_keywords: list[str] = Field(default_factory=list)
    target_audience: str = Field(default="")
    search_intent: str = Field(default="")
    meta_title: str = Field(default="")
    meta_description: str = Field(default="")
    content: str = Field(default="")
    faq: list[dict] = Field(default_factory=list)
    internal_links: list[dict] = Field(default_factory=list)
    external_links: list[dict] = Field(default_factory=list)
    images: list[dict] = Field(default_factory=list)


class BlogReviewResponse(BaseModel):
    success: bool = Field(default=True)
    report: QualityReport | None = Field(default=None)
    error: str | None = Field(default=None)
