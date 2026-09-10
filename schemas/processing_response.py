"""Pydantic schemas for the transcript processing API endpoint."""

from pydantic import BaseModel, Field

from models.processing_result import (
    LanguageDistribution,
    ProcessingStatistics,
    ProcessingStep,
    ProcessedTimestamp,
    ProcessingFlags,
)


class ProcessTranscriptRequest(BaseModel):
    video_id: str = Field(..., description="11-character YouTube video ID")
    remove_fillers: bool = Field(default=False, description="Remove filler words (um, uh, like, etc.)")


class ProcessTranscriptResponse(BaseModel):
    success: bool = True
    video_id: str = ""
    language: LanguageDistribution | None = None
    statistics: ProcessingStatistics = Field(default_factory=ProcessingStatistics)
    clean_transcript: str = ""
    paragraphs: list[str] = Field(default_factory=list)
    sentences: list[str] = Field(default_factory=list)
    processing_steps: list[ProcessingStep] = Field(default_factory=list)
    timestamps: list[ProcessedTimestamp] = Field(default_factory=list)
    flags: ProcessingFlags = Field(default_factory=ProcessingFlags)
    processing_time_ms: float = 0.0
    error: str | None = None
