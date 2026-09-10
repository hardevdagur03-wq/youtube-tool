"""Pydantic models for Phase 7 — AI Blog Generation Engine."""

from __future__ import annotations
from pydantic import BaseModel, Field


class BlogSubSection(BaseModel):
    heading: str = Field(default="")
    content: str = Field(default="")


class CalloutBox(BaseModel):
    type: str = Field(default="note", description="tip|warning|note|best_practice")
    text: str = Field(default="")


class BlogSection(BaseModel):
    heading: str = Field(default="")
    content: str = Field(default="")
    subsections: list[BlogSubSection] = Field(default_factory=list)
    callout_boxes: list[CalloutBox] = Field(default_factory=list)


class FAQItem(BaseModel):
    question: str = Field(default="")
    answer: str = Field(default="")


class BlogStatistics(BaseModel):
    word_count: int = Field(default=0, ge=0)
    reading_time: str = Field(default="< 1 min")
    estimated_seo_score: float = Field(default=0.0, ge=0.0, le=100.0)


class BlogResult(BaseModel):
    seo_title: str = Field(default="")
    meta_description: str = Field(default="")
    slug: str = Field(default="")
    introduction: str = Field(default="")
    table_of_contents: list[str] = Field(default_factory=list)
    sections: list[BlogSection] = Field(default_factory=list)
    faq: list[FAQItem] = Field(default_factory=list)
    conclusion: str = Field(default="")
    call_to_action: str = Field(default="")
    markdown: str = Field(default="")
    statistics: BlogStatistics = Field(default_factory=BlogStatistics)


class BlogGenerationResult(BaseModel):
    success: bool = Field(default=True)
    video_id: str = Field(default="")
    blog: BlogResult = Field(default_factory=BlogResult)
    llm_provider: str = Field(default="")
    llm_model: str = Field(default="")
    prompt_version: str = Field(default="")
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    cost_estimate: float = Field(default=0.0)
    generation_time_ms: float = Field(default=0.0)
    error: str | None = Field(default=None)


class BlogGenerationRequest(BaseModel):
    video_id: str = Field(default="", min_length=11, max_length=11)
    transcript: str = Field(default="", min_length=1)
    metadata: dict | None = Field(default=None)
    analysis: dict | None = Field(default=None)
    llm_provider: str | None = Field(default=None)
    llm_model: str | None = Field(default=None)
