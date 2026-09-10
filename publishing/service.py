from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from publishing.models import (
    DownloadInfo, ExportFileInfo, ExportFormat, ExportRequest, ExportResult,
)
from publishing.engine import ExportEngine
from publishing.cache_manager import CacheManager
from publishing.version_manager import VersionManager
from publishing.download_manager import DownloadManager

logger = logging.getLogger(__name__)


class PublishingService:
    def __init__(self, engine: ExportEngine | None = None):
        self.engine = engine or ExportEngine()
        self.cache = self.engine.cache_manager
        self.version_manager = self.engine.version_manager
        self.download_manager = self.engine.download_manager

    def create_export(self, project_id: str, formats: list[ExportFormat] | None = None,
                      project_data: dict[str, Any] | None = None,
                      extra_schema_data: dict[str, Any] | None = None,
                      base_url: str = "", include_package: bool = True,
                      include_manifest: bool = True, use_cache: bool = True,
                      run_validation: bool = True) -> ExportResult:
        version = self.version_manager.next_version(project_id)
        export_id = str(uuid.uuid4())

        request = ExportRequest(
            export_id=export_id,
            project_id=project_id,
            version=version,
            formats=formats,
            include_package=include_package,
            include_manifest=include_manifest,
            use_cache=use_cache,
            run_validation=run_validation,
            title=project_data.get("name", "") if project_data else "",
            content=project_data.get("content", "") if project_data else "",
            seo_title=project_data.get("seo_title", "") if project_data else "",
            meta_description=project_data.get("meta_description", "") if project_data else "",
            author=project_data.get("author", "") if project_data else "",
            language=project_data.get("language", "en") if project_data else "en",
            tags=project_data.get("tags", []) if project_data else [],
            category=project_data.get("category", "") if project_data else "",
            primary_keyword=project_data.get("primary_keyword", "") if project_data else "",
            secondary_keywords=project_data.get("secondary_keywords", []) if project_data else [],
            sections=project_data.get("sections", []) if project_data else [],
            images=project_data.get("images", []) if project_data else [],
            tables=project_data.get("tables", []) if project_data else [],
            faq=project_data.get("faq", []) if project_data else [],
            introduction=project_data.get("introduction", "") if project_data else "",
            conclusion=project_data.get("conclusion", "") if project_data else "",
            call_to_action=project_data.get("call_to_action", "") if project_data else "",
            references=project_data.get("references", []) if project_data else [],
        )

        result = self.engine.export(
            request, project_data=project_data,
            extra_schema_data=extra_schema_data, base_url=base_url,
        )

        return result

    def get_export_result(self, export_id: str) -> ExportResult | None:
        export_dir = self.engine.base_output_dir / export_id
        if not export_dir.exists():
            return None
        manifest_path = export_dir / "manifest.json"
        if not manifest_path.exists():
            return None
        import json
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            return ExportResult(
                export_id=export_id,
                project_id=data.get("project_id", ""),
                version=data.get("version", 1),
                title=data.get("title", ""),
                formats=[ExportFormat(f["format"]) for f in data.get("files", [])
                         if "format" in f],
                files=[ExportFileInfo(**f) for f in data.get("files", [])
                       if all(k in f for k in ("filename", "format", "size_bytes"))],
                total_files=len(data.get("files", [])),
                total_size_bytes=sum(f.get("size_bytes", 0) for f in data.get("files", [])),
                success=True,
                output_dir=str(export_dir),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to read export result %s: %s", export_id, e)
            return None

    def get_versions(self, project_id: str) -> list[dict[str, Any]]:
        versions = self.version_manager.list_versions(project_id)
        return [
            {
                "version": v.version,
                "created_at": v.created_at,
                "project_id": v.project_id,
                "file_count": len(v.files),
                "checksum": v.checksum,
            }
            for v in versions
        ]

    def get_version(self, project_id: str, version: int) -> dict[str, Any] | None:
        v = self.version_manager.get(project_id, version)
        if not v:
            return None
        return v.model_dump()

    def create_download_token(self, export_id: str, format_name: str,
                              project_id: str) -> DownloadInfo | None:
        export_dir = self.engine.base_output_dir / export_id
        fmt = ExportFormat(format_name) if format_name in ExportFormat._value2member_map_ else None
        if not fmt:
            return None

        ext = {
            ExportFormat.MARKDOWN: ".md",
            ExportFormat.HTML: ".html",
            ExportFormat.DOCX: ".docx",
            ExportFormat.PDF: ".pdf",
            ExportFormat.TXT: ".txt",
            ExportFormat.JSON: ".json",
        }.get(fmt, ".md")

        file_path = export_dir / f"blog{ext}"
        if not file_path.exists():
            package_path = export_dir.parent / f"blog_v{1}.zip"
            if package_path.exists():
                file_path = package_path

        if not file_path.exists():
            return None

        return self.download_manager.create_token(
            file_path=file_path, export_id=export_id,
            format_name=format_name, filename=file_path.name,
        )

    def get_download_info(self, token: str) -> DownloadInfo | None:
        return self.download_manager.validate_token(token)

    def clear_cache(self, project_id: str | None = None) -> int:
        if project_id:
            return self.cache.invalidate(project_id)
        return self.cache.clear_all()
