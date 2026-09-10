"""Pydantic models for the Outline Generation Engine.

Complete outline.json schema.
No existing code is modified.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class TitleInfo(BaseModel):
    primary_title: str = ""
    seo_title: str = ""
    ctr_title: str = ""
    alternative_titles: list[str] = Field(default_factory=list)
    seo_score: float = 0.0
    ctr_score: float = 0.0
    keyword_coverage: float = 0.0
    length: int = 0
    pixel_width: int = 0


class IntroPlan(BaseModel):
    hook_approach: str = ""
    problem_intro: str = ""
    context: str = ""
    importance_statement: str = ""
    reader_promise: str = ""
    reader_expectation: str = ""
    transition: str = ""
    target_word_count: int = 150


class ProblemAnalysis(BaseModel):
    primary_problem: str = ""
    secondary_problems: list[str] = Field(default_factory=list)
    business_impact: str = ""
    reader_pain_points: list[str] = Field(default_factory=list)
    importance: str = ""
    urgency: str = ""
    opportunity: str = ""


class SectionPlan(BaseModel):
    heading: str = ""
    heading_tag: str = "h2"
    goal: str = ""
    summary: str = ""
    key_concepts: list[str] = Field(default_factory=list)
    supporting_facts: list[str] = Field(default_factory=list)
    statistics: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    recommended_tables: list[str] = Field(default_factory=list)
    recommended_images: list[str] = Field(default_factory=list)
    target_word_count: int = 200
    priority: int = 5
    dependencies: list[str] = Field(default_factory=list)
    order: int = 0
    has_code: bool = False


class TableRecommendation(BaseModel):
    title: str = ""
    columns: list[str] = Field(default_factory=list)
    purpose: str = ""
    placement_section: str = ""
    row_count: int = 0
    priority: int = 5


class ImageRecommendation(BaseModel):
    type: str = "diagram"
    purpose: str = ""
    placement_section: str = ""
    alt_text_suggestion: str = ""
    priority: int = 5
    description: str = ""


class ExamplePlan(BaseModel):
    type: str = "real_world"
    topic: str = ""
    placement_section: str = ""
    purpose: str = ""
    priority: int = 5


class FAQPlan(BaseModel):
    question: str = ""
    answer_summary: str = ""
    intent: str = "informational"
    recommended_answer_length: int = 100
    priority: int = 5
    placement_section: str = "faq"


class CTAInfo(BaseModel):
    type: str = "primary"
    text: str = ""
    placement_section: str = "conclusion"
    intent: str = "engagement"
    priority: int = 5


class SummaryPlan(BaseModel):
    key_takeaways: list[str] = Field(default_factory=list)
    final_thoughts: str = ""
    action_items: list[str] = Field(default_factory=list)
    recap_points: list[str] = Field(default_factory=list)
    closing_strategy: str = ""
    target_word_count: int = 150


class WordCountPlan(BaseModel):
    total_minimum: int = 1200
    total_maximum: int = 3000
    total_target: int = 2000
    per_section_target: int = 200
    introduction: int = 150
    body_per_section: int = 250
    conclusion: int = 150
    section_word_counts: dict[str, int] = Field(default_factory=dict)


class ReadingTimeInfo(BaseModel):
    minutes: int = 0
    seconds: int = 0
    reading_level: str = "intermediate"
    complexity: str = "moderate"
    audience_match: float = 0.7
    content_depth: str = "standard"


class OutlineMetadata(BaseModel):
    version: str = "1.0"
    created_at: str = ""
    project_id: str = ""
    video_id: str = ""
    source_artifacts: list[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    total_sections: int = 0
    total_tables: int = 0
    total_images: int = 0
    quality_score: float = 0.0


class ContentOutline(BaseModel):
    """Complete content outline — master blueprint for content generation."""

    metadata: OutlineMetadata = Field(default_factory=OutlineMetadata)

    title: TitleInfo = Field(default_factory=TitleInfo)
    intro_plan: IntroPlan = Field(default_factory=IntroPlan)
    problem_analysis: ProblemAnalysis = Field(default_factory=ProblemAnalysis)

    sections: list[SectionPlan] = Field(default_factory=list)
    tables: list[TableRecommendation] = Field(default_factory=list)
    images: list[ImageRecommendation] = Field(default_factory=list)
    examples: list[ExamplePlan] = Field(default_factory=list)
    faqs: list[FAQPlan] = Field(default_factory=list)
    ctas: list[CTAInfo] = Field(default_factory=list)
    summary_plan: SummaryPlan = Field(default_factory=SummaryPlan)

    word_count_plan: WordCountPlan = Field(default_factory=WordCountPlan)
    reading_time: ReadingTimeInfo = Field(default_factory=ReadingTimeInfo)

    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "title": self.title.primary_title,
            "total_sections": len(self.sections),
            "total_tables": len(self.tables),
            "total_images": len(self.images),
            "total_examples": len(self.examples),
            "total_faqs": len(self.faqs),
            "total_ctas": len(self.ctas),
            "target_word_count": self.word_count_plan.total_target,
            "reading_time_minutes": self.reading_time.minutes,
            "reading_level": self.reading_time.reading_level,
            "quality_score": round(self.metadata.quality_score, 1),
        }

    def has_section(self, heading: str) -> bool:
        return any(s.heading == heading for s in self.sections)

    def get_section(self, heading: str) -> SectionPlan | None:
        for s in self.sections:
            if s.heading == heading:
                return s
        return None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
