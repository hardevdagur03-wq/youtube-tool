"""Export & Content Delivery Configuration — all settings environment-driven."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default


def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key, "").lower().strip()
    if not val:
        return default
    return val in ("1", "true", "yes", "y")


@dataclass
class ExportDeliveryConfig:
    """Configuration for Export & Content Delivery — all env-driven."""

    # Default template
    default_template: str = _env("EXPORT_DEFAULT_TEMPLATE", "default")

    # Export formats enabled
    formats_enabled: list[str] = field(default_factory=lambda: [
        "markdown", "html", "docx", "pdf", "txt", "json",
        "seo_json", "yaml_metadata", "jsonld_schema",
    ])

    # Quality validation
    quality_validation_enabled: bool = _env_bool("EXPORT_QUALITY_VALIDATION_ENABLED", True)
    quality_block_on_failure: bool = _env_bool("EXPORT_QUALITY_BLOCK_ON_FAILURE", True)

    # Image optimization
    image_optimization_enabled: bool = _env_bool("EXPORT_IMAGE_OPTIMIZATION_ENABLED", True)
    image_quality: int = _env_int("EXPORT_IMAGE_QUALITY", 85)
    image_max_width: int = _env_int("EXPORT_IMAGE_MAX_WIDTH", 1920)
    image_generate_responsive: bool = _env_bool("EXPORT_IMAGE_RESPONSIVE", True)
    image_responsive_widths: list[int] = field(default_factory=lambda: [320, 640, 1024])

    # Download service
    download_token_expiry: int = _env_int("EXPORT_DOWNLOAD_TOKEN_EXPIRY", 3600)
    download_base_url: str = _env("EXPORT_DOWNLOAD_BASE_URL", "")

    # Output directory
    output_dir: str = _env("EXPORT_OUTPUT_DIR", "exports_delivery")

    # Performance targets
    target_markdown_ms: int = _env_int("EXPORT_TARGET_MARKDOWN_MS", 2000)
    target_html_ms: int = _env_int("EXPORT_TARGET_HTML_MS", 3000)
    target_docx_ms: int = _env_int("EXPORT_TARGET_DOCX_MS", 8000)
    target_pdf_ms: int = _env_int("EXPORT_TARGET_PDF_MS", 10000)
    target_zip_ms: int = _env_int("EXPORT_TARGET_ZIP_MS", 5000)

    @classmethod
    def from_env(cls) -> ExportDeliveryConfig:
        return cls()
