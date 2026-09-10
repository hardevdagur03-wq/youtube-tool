"""Constants and targets for Export & Content Delivery."""

from __future__ import annotations

# Supported export formats
FORMATS = {
    "markdown": {"label": "Markdown", "ext": ".md", "mime": "text/markdown", "desc": "GitHub-Flavored Markdown"},
    "html": {"label": "HTML", "ext": ".html", "mime": "text/html", "desc": "Semantic HTML5 Document"},
    "docx": {"label": "DOCX", "ext": ".docx", "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "desc": "Microsoft Word Document"},
    "pdf": {"label": "PDF", "ext": ".pdf", "mime": "application/pdf", "desc": "Portable Document Format"},
    "txt": {"label": "Plain Text", "ext": ".txt", "mime": "text/plain", "desc": "Plain Text Document"},
    "json": {"label": "JSON", "ext": ".json", "mime": "application/json", "desc": "Structured JSON Export"},
    "seo_json": {"label": "SEO JSON", "ext": ".json", "mime": "application/json", "desc": "SEO Analysis Report"},
    "yaml_metadata": {"label": "Metadata", "ext": ".yaml", "mime": "text/yaml", "desc": "YAML Metadata File"},
    "jsonld_schema": {"label": "Schema.org JSON-LD", "ext": ".jsonld", "mime": "application/ld+json", "desc": "Schema.org Structured Data"},
}

# Performance targets (milliseconds)
PERFORMANCE_TARGETS = {
    "markdown": 2000,
    "html": 3000,
    "docx": 8000,
    "pdf": 10000,
    "zip": 5000,
    "download_ready": 2000,
}

# Quality thresholds
QUALITY_MIN_FILE_SIZE = 50  # bytes
QUALITY_MIN_MARKDOWN_CHARS = 20
QUALITY_MIN_PDF_SIZE = 1000  # bytes
QUALITY_MAX_FORMATTING_ERRORS = 0

# Image optimization
IMAGE_QUALITY_DEFAULT = 85
IMAGE_MAX_WIDTH = 1920
IMAGE_RESPONSIVE_WIDTHS = [320, 640, 1024]
IMAGE_PLACEHOLDER_SIZE = 20

# Template defaults
TEMPLATE_DEFAULT = "default"
TEMPLATES = ["default", "corporate", "minimal", "academic", "technical"]

# Download
DOWNLOAD_TOKEN_EXPIRY_DEFAULT = 3600  # 1 hour
DOWNLOAD_TOKEN_BYTES = 32
