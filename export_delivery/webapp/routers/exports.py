"""Export API endpoints for the Content Delivery platform."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from export_delivery.manager import ExportManager
from export_delivery.router import ExportRouter
from export_delivery.template_engine import TemplateEngine
from export_delivery.formatting_engine import FormattingEngine
from export_delivery.download_service import DownloadService
from export_delivery.quality_validator import QualityValidator
from export_delivery.exporters import (
    ProfessionalMarkdownExporter,
    EnhancedHTMLExporter,
    ProfessionalDOCXExporter,
    ProfessionalPDFExporter,
    SEOJSONExporter,
    YAMLMetadataExporter,
    JSONLDSchemaExporter,
)

router = APIRouter(prefix="/api/v3/exports", tags=["exports"])

# Global instances
_manager: ExportManager | None = None
_download_service: DownloadService | None = None
_validator: QualityValidator | None = None
_template_engine: TemplateEngine | None = None


def initialize(
    download_service: DownloadService | None = None,
    validator: QualityValidator | None = None,
) -> None:
    """Initialize the export API with services."""
    global _manager, _download_service, _validator, _template_engine

    template_engine = TemplateEngine()
    formatting_engine = FormattingEngine()
    router_engine = ExportRouter()

    # Register all exporters
    router_engine.register("markdown", ProfessionalMarkdownExporter())
    router_engine.register("html", EnhancedHTMLExporter())
    router_engine.register("docx", ProfessionalDOCXExporter())
    router_engine.register("pdf", ProfessionalPDFExporter())
    router_engine.register("seo_json", SEOJSONExporter())
    router_engine.register("yaml_metadata", YAMLMetadataExporter())
    router_engine.register("jsonld_schema", JSONLDSchemaExporter())

    _manager = ExportManager(router=router_engine, template_engine=template_engine, formatting_engine=formatting_engine)
    _download_service = download_service or DownloadService()
    _validator = validator or QualityValidator()
    _template_engine = template_engine


class ExportRequest(BaseModel):
    project_id: str = ""
    title: str = ""
    content: str = ""
    author: str = ""
    meta_description: str = ""
    formats: list[str] = ["markdown", "html"]
    template: str = "default"
    sections: list[dict] = []
    faq: list[dict] = []
    tags: list[str] = []
    category: str = ""
    word_count: int = 0
    reading_time: int = 0


@router.post("/create")
async def create_export(req: ExportRequest):
    """Create exports for specified formats."""
    if _manager is None:
        raise HTTPException(status_code=503, detail="Export service not initialized")

    doc = req
    result = _manager.export(doc, formats=req.formats, template=req.template)

    return {
        "success": True,
        "job_id": result.job_id,
        "formats_completed": result.formats_completed,
        "formats_failed": result.formats_failed,
        "files": result.files,
        "execution_time_ms": result.execution_time_ms,
        "errors": result.errors,
    }


@router.get("/templates")
async def list_templates():
    """List available export templates."""
    if _template_engine is None:
        raise HTTPException(status_code=503, detail="Template engine not initialized")
    return {"success": True, "templates": _template_engine.list_templates()}


@router.get("/formats")
async def list_formats():
    """List supported export formats."""
    from export_delivery.constants import FORMATS
    return {
        "success": True,
        "formats": [
            {"key": k, **v} for k, v in FORMATS.items()
        ],
    }
