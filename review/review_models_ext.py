"""Extended Pydantic models for comprehensive review_report.json schema."""

from __future__ import annotations
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ReviewMetadata(BaseModel):
    blog_title: str = Field(default="")
    project_id: str = Field(default="")
    url: str = Field(default="")
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    execution_time_ms: float = Field(default=0.0)
    word_count: int = Field(default=0)
    estimated_reading_time: str = Field(default="")
    primary_keyword: str = Field(default="")
    secondary_keywords: list[str] = Field(default_factory=list)
    target_audience: str = Field(default="")
    search_intent: str = Field(default="")


class GrammarReport(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    spelling_errors: int = Field(default=0)
    grammar_errors: int = Field(default=0)
    punctuation_errors: int = Field(default=0)
    passive_voice_sentences: int = Field(default=0)
    run_on_sentences: int = Field(default=0)
    sentence_fragments: int = Field(default=0)
    issues: list[dict] = Field(default_factory=list)


class SEOReport(BaseModel):
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


class ReadabilityReport(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    flesch_reading_ease: float = Field(default=0.0)
    flesch_kincaid_grade: float = Field(default=0.0)
    avg_sentence_length: float = Field(default=0.0)
    avg_paragraph_length: float = Field(default=0.0)
    complex_sentence_ratio: float = Field(default=0.0)
    passive_voice_percentage: float = Field(default=0.0)
    reading_time_minutes: float = Field(default=0.0)
    difficulty_level: str = Field(default="")
    improvement_suggestions: list[str] = Field(default_factory=list)


class StructureReport(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    h1_count: int = Field(default=0)
    hierarchy_issues: list[str] = Field(default_factory=list)
    missing_headings: list[str] = Field(default_factory=list)
    skipped_levels: list[str] = Field(default_factory=list)
    duplicate_paragraphs: int = Field(default=0)
    duplicate_headings: int = Field(default=0)
    repeated_sections: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)


class KeywordReport(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    primary_keyword_density: float = Field(default=0.0)
    secondary_keyword_density: dict[str, float] = Field(default_factory=dict)
    keyword_in_title: bool = Field(default=False)
    keyword_in_first_paragraph: bool = Field(default=False)
    keyword_in_last_paragraph: bool = Field(default=False)
    keyword_in_headings: bool = Field(default=False)
    keyword_stuffing_detected: bool = Field(default=False)
    lsi_keywords_found: list[str] = Field(default_factory=list)
    lsi_keywords_missing: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class DuplicateReport(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    duplicate_paragraphs: int = Field(default=0)
    duplicate_headings: int = Field(default=0)
    repeated_sections: list[str] = Field(default_factory=list)
    merge_recommendations: list[str] = Field(default_factory=list)


class HallucinationReport(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    risk_level: str = Field(default="low")
    unsupported_claims: int = Field(default=0)
    unverifiable_statistics: int = Field(default=0)
    fabricated_references: int = Field(default=0)


class MarkdownReport(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    table_count: int = Field(default=0)
    table_issues: list[str] = Field(default_factory=list)
    image_count: int = Field(default=0)
    images_missing_alt: int = Field(default=0)
    image_issues: list[str] = Field(default_factory=list)
    link_count: int = Field(default=0)
    broken_links: list[str] = Field(default_factory=list)
    code_block_count: int = Field(default=0)
    code_block_issues: list[str] = Field(default_factory=list)
    heading_issues: list[str] = Field(default_factory=list)
    list_issues: list[str] = Field(default_factory=list)
    html_usage_detected: bool = Field(default=False)
    issues: list[str] = Field(default_factory=list)


class CompletenessReport(BaseModel):
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


class QualityScores(BaseModel):
    overall: float = Field(default=0.0, ge=0.0, le=100.0)
    grammar: float = Field(default=0.0, ge=0.0, le=100.0)
    seo: float = Field(default=0.0, ge=0.0, le=100.0)
    readability: float = Field(default=0.0, ge=0.0, le=100.0)
    structure: float = Field(default=0.0, ge=0.0, le=100.0)
    completeness: float = Field(default=0.0, ge=0.0, le=100.0)
    keyword_optimization: float = Field(default=0.0, ge=0.0, le=100.0)
    markdown_quality: float = Field(default=0.0, ge=0.0, le=100.0)
    content_quality: float = Field(default=0.0, ge=0.0, le=100.0)
    hallucination_risk: float = Field(default=100.0, ge=0.0, le=100.0)
    fact_consistency: float = Field(default=100.0, ge=0.0, le=100.0)
    eeat: float = Field(default=0.0, ge=0.0, le=100.0)
    accessibility: float = Field(default=0.0, ge=0.0, le=100.0)
    ai_detection: float = Field(default=100.0, ge=0.0, le=100.0)
    linking: float = Field(default=0.0, ge=0.0, le=100.0)


class IssueEntry(BaseModel):
    category: str = Field(default="")
    severity: str = Field(default="low")
    description: str = Field(default="")
    location: str = Field(default="")
    why_it_matters: str = Field(default="")
    recommended_fix: str = Field(default="")


class RecommendationEntry(BaseModel):
    priority: str = Field(default="nice_to_have")
    category: str = Field(default="")
    description: str = Field(default="")
    impact: str = Field(default="")
    effort: str = Field(default="")


class PublicationStatus(BaseModel):
    decision: str = Field(default="reject")
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0)
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    critical_issues_count: int = Field(default=0)
    high_issues_count: int = Field(default=0)
    medium_issues_count: int = Field(default=0)
    low_issues_count: int = Field(default=0)


class ReviewReport(BaseModel):
    metadata: ReviewMetadata = Field(default_factory=ReviewMetadata)
    grammar: GrammarReport = Field(default_factory=GrammarReport)
    seo: SEOReport = Field(default_factory=SEOReport)
    readability: ReadabilityReport = Field(default_factory=ReadabilityReport)
    structure: StructureReport = Field(default_factory=StructureReport)
    keyword_analysis: KeywordReport = Field(default_factory=KeywordReport)
    duplicate_content: DuplicateReport = Field(default_factory=DuplicateReport)
    hallucination_risk: HallucinationReport = Field(default_factory=HallucinationReport)
    markdown: MarkdownReport = Field(default_factory=MarkdownReport)
    completeness: CompletenessReport = Field(default_factory=CompletenessReport)
    quality_scores: QualityScores = Field(default_factory=QualityScores)
    issues: list[IssueEntry] = Field(default_factory=list)
    recommendations: list[RecommendationEntry] = Field(default_factory=list)
    publication_status: PublicationStatus = Field(default_factory=PublicationStatus)
