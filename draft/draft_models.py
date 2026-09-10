"""Pydantic models for the Draft Assembly Engine.

Every draft is a versioned, validated, independently-assembled document.
No content generation occurs here — only intelligent assembly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SectionType(str, Enum):
    INTRODUCTION = "introduction"
    BODY = "body"
    FAQ = "faq"
    CONCLUSION = "conclusion"
    CTA = "cta"
    SUMMARY = "summary"


class MergeStatus(str, Enum):
    PENDING = "pending"
    MERGING = "merging"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CACHED = "cached"


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class SectionValidationResult(BaseModel):
    section_id: str = ""
    filename: str = ""
    exists: bool = False
    valid: bool = False
    word_count: int = 0
    has_heading: bool = False
    heading_tag: str = ""
    heading_text: str = ""
    encoding_valid: bool = False
    markdown_valid: bool = False
    no_corruption: bool = False
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DiscoveredSection(BaseModel):
    section_id: str = ""
    filename: str = ""
    section_type: SectionType = SectionType.BODY
    heading: str = ""
    heading_tag: str = "h2"
    content: str = ""
    order: int = 0
    word_count: int = 0
    validation: SectionValidationResult = Field(default_factory=SectionValidationResult)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if self.word_count == 0 and self.content:
            object.__setattr__(self, "word_count", len(self.content.split()))


class HeadingInfo(BaseModel):
    text: str = ""
    tag: str = "h2"
    level: int = 2
    anchor_id: str = ""
    original_text: str = ""


class TableOfContentsEntry(BaseModel):
    title: str = ""
    anchor_id: str = ""
    level: int = 2
    children: list[TableOfContentsEntry] = Field(default_factory=list)


class DraftDocument(BaseModel):
    title: str = ""
    seo_title: str = ""
    meta_description: str = ""
    content: str = ""
    sections: list[DiscoveredSection] = Field(default_factory=list)
    toc: list[TableOfContentsEntry] = Field(default_factory=list)
    word_count: int = 0
    reading_time_minutes: int = 0
    section_count: int = 0
    heading_count: int = 0
    paragraph_count: int = 0
    image_count: int = 0
    table_count: int = 0
    code_block_count: int = 0
    blockquote_count: int = 0
    list_count: int = 0


class DraftVersion(BaseModel):
    version_number: int = 1
    created_at: str = ""
    content_hash: str = ""
    modified_sections: list[str] = Field(default_factory=list)
    checksum: str = ""
    merge_metadata: dict[str, Any] = Field(default_factory=dict)


class MergeLogEntry(BaseModel):
    merge_id: str = ""
    timestamp: str = ""
    version: int = 1
    status: MergeStatus = MergeStatus.COMPLETED
    sections_merged: list[str] = Field(default_factory=list)
    section_count: int = 0
    word_count: int = 0
    checksum: str = ""
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    elapsed_ms: float = 0.0
    validation_results: dict[str, SectionValidationResult] = Field(default_factory=dict)


class DraftMetadata(BaseModel):
    project_id: str = ""
    draft_version: int = 1
    status: MergeStatus = MergeStatus.PENDING
    created_at: str = ""
    updated_at: str = ""
    author: str = "AI Writing Platform"
    pipeline_version: str = "2.0"
    seo_score: float = 0.0
    quality_status: str = "pending"
    total_word_count: int = 0
    reading_time_minutes: int = 0
    section_count: int = 0
    heading_count: int = 0
    paragraph_count: int = 0
    image_count: int = 0
    table_count: int = 0
    code_block_count: int = 0
    blockquote_count: int = 0
    list_count: int = 0


class AssemblyConfig(BaseModel):
    generate_toc: bool = True
    add_horizontal_rules: bool = True
    normalize_headings: bool = True
    resolve_references: bool = True
    preserve_tables: bool = True
    preserve_images: bool = True
    preserve_code_blocks: bool = True
    min_section_word_count: int = 10
    fail_on_missing_section: bool = False
    fail_on_validation_error: bool = False
    add_metadata_header: bool = True
    add_navigation: bool = True


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_checksum(content: str) -> str:
    import hashlib
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]
