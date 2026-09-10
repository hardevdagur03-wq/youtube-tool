"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, Field


class VideoMetadataRequest(BaseModel):
    """Request schema for video metadata lookup."""

    video_id: str = Field(..., min_length=11, max_length=11, description="YouTube video ID")
