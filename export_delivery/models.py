"""Pydantic models for Export & Content Delivery."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class TemplateConfig(BaseModel):
    """Configuration for a named template."""
    name: str = "default"
    label: str = "Default Template"
    description: str = "Standard export template"
    brand_color: str = "#059669"
    secondary_color: str = "#1f2937"
    accent_color: str = "#7c3aed"
    font_family: str = "Inter, -apple-system, sans-serif"
    font_family_heading: str = "Inter, -apple-system, sans-serif"
    font_family_mono: str = "JetBrains Mono, Consolas, monospace"
    font_size_base: int = 16
    font_size_heading_scale: float = 1.25
    line_height: float = 1.6
    page_size: str = "A4"
    page_margin_mm: float = 25.4
    cover_page: bool = True
    toc_enabled: bool = True
    header_enabled: bool = True
    footer_enabled: bool = True
    watermark_text: str = ""
    css_variables: dict[str, str] = Field(default_factory=dict)
    template_metadata: dict[str, str] = Field(default_factory=dict)


class ExportFormatInfo(BaseModel):
    """Metadata about a supported export format."""
    format_key: str = ""
    label: str = ""
    extension: str = ""
    mime_type: str = ""
    description: str = ""
    enabled: bool = True


class ExportJobRequest(BaseModel):
    """Request to create an export."""
    project_id: str = ""
    version: int = 0
    formats: list[str] = Field(default_factory=list)
    template: str = "default"
    include_bundle: bool = True
    compress_images: bool = True
    run_validation: bool = True


class ExportJobResult(BaseModel):
    """Result of an export job."""
    job_id: str = ""
    project_id: str = ""
    status: str = "pending"
    formats_completed: list[str] = Field(default_factory=list)
    formats_failed: list[str] = Field(default_factory=list)
    files: list[dict[str, Any]] = Field(default_factory=list)
    bundle_url: str = ""
    total_size_bytes: int = 0
    execution_time_ms: float = 0.0
    errors: list[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class DownloadLink(BaseModel):
    """A signed download link."""
    url: str = ""
    token: str = ""
    filename: str = ""
    format_key: str = ""
    expires_at: str = ""
    size_bytes: int = 0
    mime_type: str = ""
