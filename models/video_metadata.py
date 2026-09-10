"""Pydantic models for YouTube video metadata responses."""

from pydantic import BaseModel, Field


class DurationInfo(BaseModel):
    """Duration in multiple formats."""

    iso: str | None = Field(default=None, description="ISO 8601 duration string")
    readable: str | None = Field(default=None, description="Human-readable (e.g. '1 hr 25 min')")
    compact: str | None = Field(default=None, description="Compact format (e.g. '1:25:17')")
    seconds: int | None = Field(default=None, description="Total seconds")


class VideoStatistics(BaseModel):
    """Video statistics from the YouTube API."""

    views: int = Field(default=0)
    likes: int = Field(default=0)
    comments: int = Field(default=0)
    views_formatted: str = Field(default="0")
    likes_formatted: str = Field(default="0")
    comments_formatted: str = Field(default="0")


class Thumbnails(BaseModel):
    """Available thumbnail URLs for a video."""

    default: str | None = Field(default=None)
    medium: str | None = Field(default=None)
    high: str | None = Field(default=None)
    standard: str | None = Field(default=None)
    maxres: str | None = Field(default=None)


class DateInfo(BaseModel):
    """Date information in multiple formats."""

    iso: str | None = Field(default=None)
    localized: str | None = Field(default=None)
    relative: str | None = Field(default=None)


class DescriptionInfo(BaseModel):
    """Processed description fields."""

    full: str | None = Field(default=None, description="Full raw description")
    urls: list[str] = Field(default_factory=list, description="Extracted URLs")
    hashtags: list[str] = Field(default_factory=list, description="Extracted hashtags")
    mentions: list[str] = Field(default_factory=list, description="Extracted @mentions")


class ChannelInfo(BaseModel):
    """Channel information for a video."""

    name: str | None = Field(default=None)
    id: str | None = Field(default=None)
    url: str | None = Field(default=None)
    verified: bool | None = Field(default=None)


class VideoMetadata(BaseModel):
    """Complete video metadata from the YouTube Data API v3."""

    video_id: str
    title: str | None = Field(default=None)
    description: DescriptionInfo = Field(default_factory=DescriptionInfo)
    channel: ChannelInfo = Field(default_factory=ChannelInfo)
    published_at: DateInfo = Field(default_factory=DateInfo)
    duration: DurationInfo = Field(default_factory=DurationInfo)
    statistics: VideoStatistics = Field(default_factory=VideoStatistics)
    thumbnails: Thumbnails = Field(default_factory=Thumbnails)
    tags: list[str] = Field(default_factory=list)
    category_id: str | None = Field(default=None)
    language: str | None = Field(default=None)
    license: str | None = Field(default=None)
    embeddable: bool | None = Field(default=None)
    caption: bool | None = Field(default=None)
    privacy: str | None = Field(default=None)
    live_status: str | None = Field(default=None)
    default_audio_language: str | None = Field(default=None)


class VideoMetadataResponse(BaseModel):
    """API response wrapper for video metadata."""

    success: bool
    video: VideoMetadata | None = Field(default=None)
    error: str | None = Field(default=None)
