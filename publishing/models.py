from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExportFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    DOCX = "docx"
    PDF = "pdf"
    TXT = "txt"
    JSON = "json"
    SCHEMA = "schema"
    PACKAGE = "package"


FORMAT_EXTENSIONS: dict[ExportFormat, str] = {
    ExportFormat.MARKDOWN: ".md",
    ExportFormat.HTML: ".html",
    ExportFormat.DOCX: ".docx",
    ExportFormat.PDF: ".pdf",
    ExportFormat.TXT: ".txt",
    ExportFormat.JSON: ".json",
    ExportFormat.SCHEMA: ".json",
    ExportFormat.PACKAGE: ".zip",
}

FORMAT_MIME_TYPES: dict[ExportFormat, str] = {
    ExportFormat.MARKDOWN: "text/markdown",
    ExportFormat.HTML: "text/html",
    ExportFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ExportFormat.PDF: "application/pdf",
    ExportFormat.TXT: "text/plain",
    ExportFormat.JSON: "application/json",
    ExportFormat.SCHEMA: "application/json",
    ExportFormat.PACKAGE: "application/zip",
}


class ExportFileInfo(BaseModel):
    format: ExportFormat
    filename: str
    size_bytes: int = 0
    size_display: str = ""
    mime_type: str = ""
    checksum: str = ""
    valid: bool = True
    validation_message: str = ""


class ExportRequest(BaseModel):
    export_id: str = ""
    project_id: str = ""
    version: int = 1
    formats: list[ExportFormat] = Field(default_factory=lambda: [f for f in ExportFormat if f not in (ExportFormat.SCHEMA, ExportFormat.PACKAGE)])
    include_package: bool = True
    include_manifest: bool = True
    use_cache: bool = True
    run_validation: bool = True
    title: str = ""
    content: str = ""
    seo_title: str = ""
    meta_description: str = ""
    author: str = ""
    language: str = "en"
    tags: list[str] = Field(default_factory=list)
    category: str = ""
    primary_keyword: str = ""
    secondary_keywords: list[str] = Field(default_factory=list)
    sections: list[Any] = Field(default_factory=list)
    images: list[Any] = Field(default_factory=list)
    tables: list[Any] = Field(default_factory=list)
    faq: list[dict[str, str]] = Field(default_factory=list)
    introduction: str = ""
    conclusion: str = ""
    call_to_action: str = ""
    references: list[dict[str, str]] = Field(default_factory=list)


class ExportResult(BaseModel):
    export_id: str = ""
    project_id: str = ""
    version: int = 1
    title: str = ""
    formats: list[ExportFormat] = Field(default_factory=list)
    files: list[ExportFileInfo] = Field(default_factory=list)
    total_files: int = 0
    total_size_bytes: int = 0
    total_size_display: str = ""
    output_dir: str = ""
    execution_time_ms: int = 0
    success: bool = True
    errors: list[str] = Field(default_factory=list)
    validation_results: list[ValidationResult] = Field(default_factory=list)


class ExportMetadata(BaseModel):
    export_id: str = ""
    project_id: str = ""
    version: int = 1
    created_at: str = Field(default_factory=utc_now)
    formats: list[str] = Field(default_factory=list)
    total_size_bytes: int = 0
    file_count: int = 0
    checksums: dict[str, str] = Field(default_factory=dict)
    execution_time_ms: float = 0.0


class ExportVersion(BaseModel):
    project_id: str = ""
    version: int = 1
    created_at: str = Field(default_factory=utc_now)
    files: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    checksum: str = ""


class ExportCacheEntry(BaseModel):
    key: str = ""
    project_id: str = ""
    format: str = ""
    version: int = 0
    file_info: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)
    ttl: int = 3600


class SectionInfo(BaseModel):
    heading: str = ""
    heading_tag: str = "h2"
    content: str = ""
    subsections: list[SectionInfo] = Field(default_factory=list)
    order: int = 0
    word_count: int = 0


class ImageInfo(BaseModel):
    url: str = ""
    alt: str = ""
    caption: str = ""
    filename: str = ""
    local_path: str = ""
    width: int = 0
    height: int = 0


class TableInfo(BaseModel):
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    caption: str = ""
    alignment: list[str] = Field(default_factory=list)


class CodeBlockInfo(BaseModel):
    language: str = ""
    code: str = ""
    caption: str = ""


class LinkInfo(BaseModel):
    text: str = ""
    url: str = ""
    is_internal: bool = False


class HeadingInfo(BaseModel):
    text: str = ""
    tag: str = "h2"
    level: int = 2


class FAQItem(BaseModel):
    question: str = ""
    answer: str = ""


class ReferenceInfo(BaseModel):
    label: str = ""
    url: str = ""


class DocumentModel(BaseModel):
    title: str = ""
    seo_title: str = ""
    meta_description: str = ""
    content: str = ""
    sections: list[SectionInfo] = Field(default_factory=list)
    introduction: str = ""
    conclusion: str = ""
    call_to_action: str = ""
    faq: list[FAQItem] = Field(default_factory=list)
    references: list[ReferenceInfo] = Field(default_factory=list)
    toc: list[str] = Field(default_factory=list)
    images: list[ImageInfo] = Field(default_factory=list)
    tables: list[TableInfo] = Field(default_factory=list)
    code_blocks: list[CodeBlockInfo] = Field(default_factory=list)
    links: list[LinkInfo] = Field(default_factory=list)
    headings: list[HeadingInfo] = Field(default_factory=list)
    word_count: int = 0
    reading_time_minutes: int = 0
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    primary_keyword: str = ""
    secondary_keywords: list[str] = Field(default_factory=list)
    author: str = ""
    publish_date: str = ""
    language: str = "en"
    image_count: int = 0
    headings_text: list[str] = Field(default_factory=list)


class ManifestInfo(BaseModel):
    project_id: str = ""
    export_id: str = ""
    version: int = 1
    created_at: str = Field(default_factory=utc_now)
    title: str = ""
    formats: list[str] = Field(default_factory=list)
    files: list[dict[str, Any]] = Field(default_factory=list)
    checksums: dict[str, str] = Field(default_factory=dict)
    statistics: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationResult(BaseModel):
    check: str = ""
    severity: ValidationSeverity = ValidationSeverity.INFO
    message: str = ""
    context: dict[str, Any] = Field(default_factory=dict)


class SchemaMarkup(BaseModel):
    type: str = "Article"
    data: dict[str, Any] = Field(default_factory=dict)


class OpenGraphData(BaseModel):
    title: str = ""
    description: str = ""
    type: str = "article"
    url: str = ""
    image: str = ""
    site_name: str = ""
    locale: str = "en_US"
    published_time: str = ""
    author: str = ""


class TwitterCardData(BaseModel):
    card: str = "summary_large_image"
    title: str = ""
    description: str = ""
    image: str = ""
    site: str = ""


class PackageInfo(BaseModel):
    package_id: str = ""
    export_id: str = ""
    filename: str = ""
    size_bytes: int = 0
    size_display: str = ""
    checksum: str = ""
    file_count: int = 0
    manifest: ManifestInfo | None = None
    created_at: str = Field(default_factory=utc_now)


class DownloadInfo(BaseModel):
    token: str = ""
    token_hash: str = ""
    file_path: str = ""
    export_id: str = ""
    format: str = ""
    filename: str = ""
    expires_at: float = 0.0
    download_count: int = 0
