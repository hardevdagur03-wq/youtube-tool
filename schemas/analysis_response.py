"""API schemas for content analysis endpoints."""

from __future__ import annotations
from pydantic import BaseModel, Field

from models.content_analysis import ContentAnalysisResult


class AnalyzeTranscriptRequest(BaseModel):
    video_id: str = Field(..., min_length=11, max_length=11)
    transcript: str = Field(..., min_length=1)
    metadata: dict | None = Field(default=None)
    video_statistics: dict | None = Field(default=None)
    channel_info: dict | None = Field(default=None)
    language_info: dict | None = Field(default=None)
    force_refresh: bool = Field(default=False)
    llm_provider: str | None = Field(default=None)
    llm_model: str | None = Field(default=None)


class AnalyzeTranscriptResponse(BaseModel):
    success: bool = Field(default=True)
    analysis: ContentAnalysisResult | None = Field(default=None)
    error: str | None = Field(default=None)
