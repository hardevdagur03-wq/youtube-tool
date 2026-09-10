"""Pydantic models for Phase 10 — Multi-Format Export Engine."""

from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field


class ExportFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    DOCX = "docx"
    PDF = "pdf"


class ExportFile(BaseModel):
    format: str
    filename: str
    size_bytes: int = Field(default=0)
    size_display: str = Field(default="")
    download_url: str = Field(default="")
    mime_type: str = Field(default="")
    valid: bool = Field(default=True)
    validation_message: str = Field(default="")


class ExportRequest(BaseModel):
    blog_title: str = Field(default="")
    slug: str = Field(default="")
    meta_title: str = Field(default="")
    meta_description: str = Field(default="")
    author: str = Field(default="")
    publish_date: str = Field(default="")
    category: str = Field(default="")
    tags: list[str] = Field(default_factory=list)
    primary_keyword: str = Field(default="")
    secondary_keywords: list[str] = Field(default_factory=list)
    introduction: str = Field(default="")
    table_of_contents: list[str] = Field(default_factory=list)
    sections: list[dict] = Field(default_factory=list)
    faq: list[dict] = Field(default_factory=list)
    conclusion: str = Field(default="")
    call_to_action: str = Field(default="")
    references: list[dict] = Field(default_factory=list)
    images: list[dict] = Field(default_factory=list)
    internal_links: list[dict] = Field(default_factory=list)
    external_links: list[dict] = Field(default_factory=list)
    markdown_content: str = Field(default="")
    word_count: int = Field(default=0)
    reading_time: str = Field(default="")
    formats: list[ExportFormat] = Field(
        default_factory=lambda: [f for f in ExportFormat]
    )
    compress: bool = Field(default=False)
    base_url: str = Field(default="https://example.com")


class ExportResult(BaseModel):
    success: bool = Field(default=True)
    export_id: str = Field(default="")
    generated_files: list[ExportFile] = Field(default_factory=list)
    zip_download: str | None = Field(default=None)
    file_count: int = Field(default=0)
    total_size_bytes: int = Field(default=0)
    total_size_display: str = Field(default="")
    execution_time_ms: float = Field(default=0.0)
    error: str | None = Field(default=None)


class DownloadToken(BaseModel):
    token: str = Field(default="")
    filename: str = Field(default="")
    export_id: str = Field(default="")
    expires_at: str = Field(default="")
