"""Pydantic models for Phase 8 — SEO Optimization Engine."""

from __future__ import annotations
from pydantic import BaseModel, Field


class KeywordDensity(BaseModel):
    primary: float = Field(default=0.0, ge=0.0, description="Primary keyword density %")
    secondary: dict[str, float] = Field(default_factory=dict)


class KeywordAnalysis(BaseModel):
    primary: str = Field(default="")
    secondary: list[str] = Field(default_factory=list)
    long_tail: list[str] = Field(default_factory=list)
    lsi: list[str] = Field(default_factory=list)
    density: KeywordDensity = Field(default_factory=KeywordDensity)
    in_title: bool = False
    in_meta: bool = False
    in_intro: bool = False
    in_headings: list[str] = Field(default_factory=list)
    in_first_paragraph: bool = False
    in_last_paragraph: bool = False


class HeadingInfo(BaseModel):
    level: int = Field(default=2, ge=1, le=6)
    text: str = Field(default="")
    has_keyword: bool = False


class HeadingAnalysis(BaseModel):
    h1_count: int = 0
    h2_count: int = 0
    h3_count: int = 0
    headings: list[HeadingInfo] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class LinkSuggestion(BaseModel):
    anchor_text: str = Field(default="")
    suggested_topic: str = Field(default="")
    suggested_url: str = Field(default="")
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)


class ImageSEO(BaseModel):
    alt_text: str = Field(default="")
    title: str = Field(default="")
    caption: str = Field(default="")
    suggested_filename: str = Field(default="")


class OpenGraph(BaseModel):
    title: str = Field(default="")
    description: str = Field(default="")
    image: str = Field(default="")
    type: str = Field(default="article")


class TwitterCard(BaseModel):
    title: str = Field(default="")
    description: str = Field(default="")
    image: str = Field(default="")
    card_type: str = Field(default="summary_large_image")


class SchemaMarkup(BaseModel):
    article: dict = Field(default_factory=dict)
    blog_posting: dict = Field(default_factory=dict)
    faq_page: dict = Field(default_factory=dict)
    breadcrumb_list: dict = Field(default_factory=dict)
    video_object: dict = Field(default_factory=dict)


class ReadabilityAnalysis(BaseModel):
    word_count: int = 0
    character_count: int = 0
    paragraph_count: int = 0
    avg_sentence_length: float = 0.0
    flesch_reading_ease: float = 0.0
    grade_level: str = Field(default="")
    passive_voice_pct: float = 0.0
    reading_time: str = Field(default="< 1 min")


class SEOStatistics(BaseModel):
    word_count: int = 0
    reading_time: str = Field(default="< 1 min")
    seo_score: float = Field(default=0.0, ge=0.0, le=100.0)


class Recommendation(BaseModel):
    priority: str = Field(default="medium", description="critical|high|medium|low")
    category: str = Field(default="")
    message: str = Field(default="")
    suggestion: str = Field(default="")


class SEOPackage(BaseModel):
    meta_title: str = Field(default="")
    meta_description: str = Field(default="")
    slug: str = Field(default="")
    canonical_url: str = Field(default="")
    keywords: KeywordAnalysis = Field(default_factory=KeywordAnalysis)
    headings: HeadingAnalysis = Field(default_factory=HeadingAnalysis)
    internal_links: list[LinkSuggestion] = Field(default_factory=list)
    external_links: list[LinkSuggestion] = Field(default_factory=list)
    image: ImageSEO = Field(default_factory=ImageSEO)
    open_graph: OpenGraph = Field(default_factory=OpenGraph)
    twitter_card: TwitterCard = Field(default_factory=TwitterCard)
    schema_markup: SchemaMarkup = Field(default_factory=SchemaMarkup)
    readability: ReadabilityAnalysis = Field(default_factory=ReadabilityAnalysis)
    statistics: SEOStatistics = Field(default_factory=SEOStatistics)
    recommendations: list[Recommendation] = Field(default_factory=list)


class SEOOptimizationResult(BaseModel):
    success: bool = Field(default=True)
    video_id: str = Field(default="")
    seo_package: SEOPackage = Field(default_factory=SEOPackage)
    llm_provider: str = Field(default="")
    llm_model: str = Field(default="")
    prompt_version: str = Field(default="")
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    cost_estimate: float = Field(default=0.0)
    optimization_time_ms: float = Field(default=0.0)
    error: str | None = Field(default=None)


class SEORequest(BaseModel):
    video_id: str = Field(default="")
    blog: dict = Field(default_factory=dict)
    metadata: dict | None = Field(default=None)
    analysis: dict | None = Field(default=None)
    llm_provider: str | None = Field(default=None)
    llm_model: str | None = Field(default=None)
