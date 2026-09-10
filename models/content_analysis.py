"""Content analysis models for Phase 6 — AI Content Analysis Engine."""

from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field


class SearchIntent(str, Enum):
    INFORMATIONAL = "informational"
    EDUCATIONAL = "educational"
    COMMERCIAL = "commercial"
    TRANSACTIONAL = "transactional"
    NAVIGATIONAL = "navigational"
    COMPARATIVE = "comparative"
    REVIEW = "review"
    TUTORIAL = "tutorial"
    OPINION = "opinion"
    CASE_STUDY = "case_study"
    RESEARCH = "research"


class ContentCategory(str, Enum):
    EDUCATION = "education"
    TECHNOLOGY = "technology"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    POLITICS = "politics"
    CAREER = "career"
    PROGRAMMING = "programming"
    AI = "ai"
    MACHINE_LEARNING = "machine_learning"
    BUSINESS = "business"
    MARKETING = "marketing"
    LIFESTYLE = "lifestyle"
    SCIENCE = "science"
    ENTERTAINMENT = "entertainment"
    SPORTS = "sports"
    NEWS = "news"
    OTHER = "other"


class ContentType(str, Enum):
    TUTORIAL = "tutorial"
    EXPLAINER = "explainer"
    REVIEW = "review"
    OPINION = "opinion"
    CASE_STUDY = "case_study"
    INTERVIEW = "interview"
    PRESENTATION = "presentation"
    DISCUSSION = "discussion"
    DOCUMENTARY = "documentary"
    VLOG = "vlog"
    PODCAST = "podcast"
    OTHER = "other"


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    ALL = "all"


class AnalysisSummary(BaseModel):
    short: str = Field(default="", description="One-sentence summary")
    executive: str = Field(default="", description="Executive summary (2-3 sentences)")
    detailed: str = Field(default="", description="Detailed summary (paragraph)")
    bullet_points: list[str] = Field(default_factory=list, description="Key bullet points")
    key_insights: list[str] = Field(default_factory=list)
    main_arguments: list[str] = Field(default_factory=list)
    important_facts: list[str] = Field(default_factory=list)
    actionable_points: list[str] = Field(default_factory=list)


class KeywordSet(BaseModel):
    primary: str = Field(default="", description="Primary keyword")
    secondary: list[str] = Field(default_factory=list, description="Secondary keywords")
    long_tail: list[str] = Field(default_factory=list, description="Long-tail keywords")
    semantic: list[str] = Field(default_factory=list, description="Semantically related keywords")
    lsi: list[str] = Field(default_factory=list, description="LSI keywords")
    related_topics: list[str] = Field(default_factory=list)
    trending_terms: list[str] = Field(default_factory=list)
    brand_names: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)


class EntitySet(BaseModel):
    people: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    universities: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    books: list[str] = Field(default_factory=list)
    courses: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    standards: list[str] = Field(default_factory=list)
    government_agencies: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    statistics: list[str] = Field(default_factory=list)


class ContentOutline(BaseModel):
    sections: list[str] = Field(default_factory=list, description="Ordered outline sections")
    introduction: str = Field(default="")
    main_body: list[str] = Field(default_factory=list)
    conclusion: str = Field(default="")


class QualityScores(BaseModel):
    topic_coverage: float = Field(default=0.0, ge=0.0, le=100.0)
    depth_score: float = Field(default=0.0, ge=0.0, le=100.0)
    readability: float = Field(default=0.0, ge=0.0, le=100.0)
    information_density: float = Field(default=0.0, ge=0.0, le=100.0)
    technical_complexity: float = Field(default=0.0, ge=0.0, le=100.0)
    educational_value: float = Field(default=0.0, ge=0.0, le=100.0)
    uniqueness: float = Field(default=0.0, ge=0.0, le=100.0)
    seo_potential: float = Field(default=0.0, ge=0.0, le=100.0)
    evergreen_score: float = Field(default=0.0, ge=0.0, le=100.0)
    engagement_potential: float = Field(default=0.0, ge=0.0, le=100.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ContentAnalysisResult(BaseModel):
    success: bool = Field(default=True)
    video_id: str = Field(default="")

    primary_topic: str = Field(default="")
    secondary_topics: list[str] = Field(default_factory=list)

    category: ContentCategory = Field(default=ContentCategory.OTHER)
    subcategory: str = Field(default="")
    content_type: ContentType = Field(default=ContentType.OTHER)
    search_intent: SearchIntent = Field(default=SearchIntent.INFORMATIONAL)
    intent_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    target_audience: str = Field(default="")
    experience_level: DifficultyLevel = Field(default=DifficultyLevel.ALL)
    industry: str = Field(default="")
    difficulty: str = Field(default="")

    content_purpose: str = Field(default="")
    problem_statement: str = Field(default="")
    main_solution: str = Field(default="")

    key_takeaways: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    call_to_actions: list[str] = Field(default_factory=list)

    learning_objectives: list[str] = Field(default_factory=list)
    business_value: str = Field(default="")
    educational_value: str = Field(default="")

    summary: AnalysisSummary = Field(default_factory=AnalysisSummary)
    keywords: KeywordSet = Field(default_factory=KeywordSet)
    entities: EntitySet = Field(default_factory=EntitySet)
    outline: ContentOutline = Field(default_factory=ContentOutline)
    quality: QualityScores = Field(default_factory=QualityScores)

    analysis_time_ms: float = Field(default=0.0)
    llm_provider: str = Field(default="")
    llm_model: str = Field(default="")
    prompt_version: str = Field(default="")
    total_tokens: int = Field(default=0)
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    cost_estimate: float = Field(default=0.0)

    error: str | None = Field(default=None)


class AnalysisRequest(BaseModel):
    video_id: str = Field(..., min_length=11, max_length=11)
    transcript: str = Field(..., min_length=1)
    metadata: dict | None = Field(default=None)
    video_statistics: dict | None = Field(default=None)
    channel_info: dict | None = Field(default=None)
    language_info: dict | None = Field(default=None)
    force_refresh: bool = Field(default=False)
    llm_provider: str | None = Field(default=None)
    llm_model: str | None = Field(default=None)
