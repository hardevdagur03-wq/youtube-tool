"""Pydantic models for the SEO Intelligence Engine.

Complete seo_plan.json schema.
No existing code is modified.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SearchIntentType(str, Enum):
    INFORMATIONAL = "informational"
    COMMERCIAL = "commercial"
    TRANSACTIONAL = "transactional"
    NAVIGATIONAL = "navigational"
    EDUCATIONAL = "educational"
    COMPARISON = "comparison"
    REVIEW = "review"
    TUTORIAL = "tutorial"


class KeywordType(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    LSI = "lsi"
    SEMANTIC = "semantic"
    LONG_TAIL = "long_tail"
    QUESTION = "question"


class CompetitionLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class ContentDepth(str, Enum):
    THIN = "thin"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"
    ULTIMATE = "ultimate"


class SchemaType(str, Enum):
    ARTICLE = "Article"
    FAQ = "FAQPage"
    HOW_TO = "HowTo"
    VIDEO = "VideoObject"
    BREADCRUMB = "BreadcrumbList"
    ORGANIZATION = "Organization"
    PERSON = "Person"
    SOFTWARE_APP = "SoftwareApplication"
    COURSE = "Course"
    PRODUCT = "Product"


# ---------------------------------------------------------------------------
# Core Models
# ---------------------------------------------------------------------------


class KeywordInfo(BaseModel):
    keyword: str
    type: KeywordType = KeywordType.SECONDARY
    search_volume_category: str = "medium"
    competition: CompetitionLevel = CompetitionLevel.MEDIUM
    difficulty: float = 0.5
    relevance: float = 0.5
    intent: str = "informational"
    priority: int = 5
    semantic_cluster: str = ""
    confidence: float = 0.7


class KeywordStrategy(BaseModel):
    primary_keyword: str = ""
    primary_volume_category: str = "medium"
    primary_difficulty: float = 0.5
    primary_intent: str = "informational"
    secondary_keywords: list[KeywordInfo] = Field(default_factory=list)
    lsi_keywords: list[str] = Field(default_factory=list)
    semantic_keywords: list[str] = Field(default_factory=list)
    long_tail_keywords: list[str] = Field(default_factory=list)
    question_keywords: list[str] = Field(default_factory=list)
    entity_keywords: list[str] = Field(default_factory=list)
    total_keyword_count: int = 0


class SearchIntent(BaseModel):
    primary_intent: SearchIntentType = SearchIntentType.INFORMATIONAL
    secondary_intent: list[SearchIntentType] = Field(default_factory=list)
    search_funnel_stage: str = "awareness"
    confidence: float = 0.7
    intent_evidence: list[str] = Field(default_factory=list)


class TargetAudience(BaseModel):
    primary_audience: str = ""
    skill_level: str = "intermediate"
    industry: list[str] = Field(default_factory=list)
    job_roles: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    learning_objectives: list[str] = Field(default_factory=list)
    buying_stage: str = "awareness"


class URLInfo(BaseModel):
    suggested_slug: str = ""
    full_url: str = ""
    length: int = 0
    keyword_included: bool = False
    stop_words_removed: bool = True
    readable_score: float = 0.9


class MetaInfo(BaseModel):
    meta_title: str = ""
    meta_title_length: int = 0
    meta_title_pixels: int = 0
    meta_title_ctr_score: float = 0.5

    meta_description: str = ""
    meta_description_length: int = 0
    meta_description_ctr_score: float = 0.5

    og_title: str = ""
    og_description: str = ""
    og_image_alt: str = ""

    twitter_title: str = ""
    twitter_description: str = ""


class HeadingSuggestion(BaseModel):
    tag: str = "h2"
    text: str = ""
    keyword_included: bool = False
    related_keywords: list[str] = Field(default_factory=list)
    order: int = 0


class HeadingStrategy(BaseModel):
    h1: str = ""
    h2_suggestions: list[HeadingSuggestion] = Field(default_factory=list)
    h3_suggestions: list[HeadingSuggestion] = Field(default_factory=list)
    total_headings: int = 0
    keyword_coverage: float = 0.0


class FAQItem(BaseModel):
    question: str = ""
    answer: str = ""
    keyword: str = ""
    priority: int = 5
    intent: str = "informational"
    schema_ready: bool = True


class SchemaMarkup(BaseModel):
    type: SchemaType = SchemaType.ARTICLE
    template: dict[str, Any] = Field(default_factory=dict)
    json_ld: str = ""
    priority: int = 5
    notes: str = ""


class FeaturedSnippetPlan(BaseModel):
    target_question: str = ""
    target_section: str = ""
    recommended_format: str = "paragraph"
    keyword: str = ""
    current_snippets: list[str] = Field(default_factory=list)
    optimization_tips: list[str] = Field(default_factory=list)
    priority: int = 5


class InternalLink(BaseModel):
    target_topic: str = ""
    suggested_anchor: str = ""
    relevance_score: float = 0.5
    priority: int = 5
    placement_suggestion: str = ""


class ExternalLink(BaseModel):
    suggested_domain: str = ""
    url_pattern: str = ""
    reason: str = ""
    authority_score: float = 0.5
    reference_type: str = "documentation"
    priority: int = 5


class CompetitorStrategy(BaseModel):
    content_angle: str = ""
    unique_value_proposition: str = ""
    differentiation_notes: str = ""
    content_gaps: list[str] = Field(default_factory=list)
    missing_topics: list[str] = Field(default_factory=list)
    authority_opportunities: list[str] = Field(default_factory=list)
    competitive_advantages: list[str] = Field(default_factory=list)


class ContentStrategy(BaseModel):
    content_angle: str = ""
    content_depth: ContentDepth = ContentDepth.STANDARD
    recommended_word_count: int = 1500
    recommended_headings: int = 8
    recommended_images: int = 3
    recommended_tables: int = 0
    recommended_examples: int = 3
    recommended_statistics: int = 2
    recommended_quotes: int = 1
    recommended_case_studies: int = 0
    recommended_code_examples: int = 0


class SEOScore(BaseModel):
    overall_score: float = 0.0
    keyword_score: float = 0.0
    intent_match_score: float = 0.0
    topic_authority_score: float = 0.0
    keyword_coverage_score: float = 0.0
    semantic_coverage_score: float = 0.0
    readability_score: float = 0.0
    ctr_prediction: float = 0.0
    completeness_score: float = 0.0
    content_opportunity_score: float = 0.0


class PlanMetadata(BaseModel):
    version: str = "1.0"
    created_at: str = ""
    project_id: str = ""
    video_id: str = ""
    source_artifacts: list[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0


class SEOPlan(BaseModel):
    """Complete SEO plan — single source of truth for all SEO decisions."""

    metadata: PlanMetadata = Field(default_factory=PlanMetadata)

    keyword_strategy: KeywordStrategy = Field(default_factory=KeywordStrategy)
    search_intent: SearchIntent = Field(default_factory=SearchIntent)
    target_audience: TargetAudience = Field(default_factory=TargetAudience)

    url: URLInfo = Field(default_factory=URLInfo)
    meta: MetaInfo = Field(default_factory=MetaInfo)
    heading_strategy: HeadingStrategy = Field(default_factory=HeadingStrategy)
    content_strategy: ContentStrategy = Field(default_factory=ContentStrategy)

    faqs: list[FAQItem] = Field(default_factory=list)
    schemas: list[SchemaMarkup] = Field(default_factory=list)
    featured_snippets: list[FeaturedSnippetPlan] = Field(default_factory=list)

    internal_links: list[InternalLink] = Field(default_factory=list)
    external_links: list[ExternalLink] = Field(default_factory=list)
    competitor_strategy: CompetitorStrategy = Field(default_factory=CompetitorStrategy)

    scores: SEOScore = Field(default_factory=SEOScore)

    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "primary_keyword": self.keyword_strategy.primary_keyword,
            "total_keywords": self.keyword_strategy.total_keyword_count,
            "search_intent": self.search_intent.primary_intent.value,
            "target_audience": self.target_audience.primary_audience,
            "meta_title": self.meta.meta_title,
            "slug": self.url.suggested_slug,
            "word_count_recommendation": self.content_strategy.recommended_word_count,
            "overall_seo_score": round(self.scores.overall_score, 1),
            "content_opportunity_score": round(self.scores.content_opportunity_score, 1),
            "faq_count": len(self.faqs),
            "schema_count": len(self.schemas),
            "featured_snippet_count": len(self.featured_snippets),
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
