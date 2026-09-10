from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from publishing.models import (
    DocumentModel, ExportFileInfo, ExportFormat, ExportRequest, ExportResult,
    FAQItem, ReferenceInfo,
    FORMAT_EXTENSIONS, FORMAT_MIME_TYPES,
)
from publishing.render_engine import RenderEngine
from publishing.markdown_exporter import MarkdownExporter
from publishing.html_exporter import HTMLExporter
from publishing.docx_exporter import DocxExporter
from publishing.pdf_exporter import PDFExporter
from publishing.txt_exporter import TxtExporter
from publishing.json_exporter import JSONExporter
from publishing.schema_exporter import SchemaExporter
from publishing.asset_manager import AssetManager
from publishing.manifest_generator import ManifestGenerator
from publishing.package_builder import PackageBuilder
from publishing.export_validator import ExportValidator
from publishing.cache_manager import CacheManager
from publishing.version_manager import VersionManager
from publishing.download_manager import DownloadManager

logger = logging.getLogger(__name__)

EXPORTERS: dict[ExportFormat, Any] = {
    ExportFormat.MARKDOWN: MarkdownExporter(),
    ExportFormat.HTML: HTMLExporter(),
    ExportFormat.DOCX: DocxExporter(),
    ExportFormat.PDF: PDFExporter(),
    ExportFormat.TXT: TxtExporter(),
    ExportFormat.JSON: JSONExporter(),
}


class ExportEngine:
    def __init__(self, base_output_dir: str | Path = "exports/publishing",
                 cache_ttl: int = 3600, use_redis: bool = False,
                 strict_validation: bool = False, max_workers: int = 4):
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(parents=True, exist_ok=True)

        self.render_engine = RenderEngine()
        self.schema_exporter = SchemaExporter()
        self.asset_manager = AssetManager()
        self.manifest_generator = ManifestGenerator()
        self.package_builder = PackageBuilder()
        self.validator = ExportValidator(strict=strict_validation)
        self.cache_manager = CacheManager(ttl=cache_ttl, use_redis=use_redis)
        self.version_manager = VersionManager()
        self.download_manager = DownloadManager()
        self.max_workers = max_workers

    def export(self, request: ExportRequest, project_data: dict[str, Any] | None = None,
               extra_schema_data: dict[str, Any] | None = None,
               base_url: str = "") -> ExportResult:
        start_time = time.time()

        output_dir = self.base_output_dir / request.export_id
        output_dir.mkdir(parents=True, exist_ok=True)

        metadata = {
            "title": request.title,
            "seo_title": request.seo_title,
            "meta_description": request.meta_description,
            "author": request.author,
            "language": request.language,
            "tags": request.tags,
            "category": request.category,
            "primary_keyword": request.primary_keyword,
            "secondary_keywords": request.secondary_keywords,
        }
        document = self.render_engine.render(request.content or "", metadata)
        document.image_count = len(document.images)
        document.headings_text = [h.text for h in document.headings]
        if request.faq and not document.faq:
            document.faq = [FAQItem(**f) if isinstance(f, dict) else f for f in request.faq]
        if request.introduction and not document.introduction:
            document.introduction = request.introduction
        if request.conclusion and not document.conclusion:
            document.conclusion = request.conclusion
        if request.call_to_action and not document.call_to_action:
            document.call_to_action = request.call_to_action
        if request.references and not document.references:
            document.references = [ReferenceInfo(**r) if isinstance(r, dict) else r for r in request.references]
        export_files: list[ExportFileInfo] = []
        validation_results = []
        errors: list[str] = []

        asset_manager = AssetManager()
        asset_manager.export_images(document, output_dir)

        formats_to_export = self._resolve_formats(request)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map = {}
            for fmt in formats_to_export:
                exporter = EXPORTERS.get(fmt)
                if not exporter:
                    errors.append(f"No exporter for format: {fmt}")
                    continue

                cache_key = fmt.value
                if request.use_cache:
                    cached = self.cache_manager.get(
                        request.project_id, cache_key, request.version
                    )
                    if cached:
                        export_files.append(ExportFileInfo(**cached.file_info))
                        continue

                future = executor.submit(
                    self._export_single, exporter, document, fmt, output_dir,
                    base_url, project_data
                )
                future_map[future] = fmt

            for future in as_completed(future_map):
                fmt = future_map[future]
                try:
                    result = future.result()
                    if isinstance(result, ExportFileInfo):
                        export_files.append(result)
                        if request.use_cache:
                            self.cache_manager.set(
                                request.project_id, fmt.value,
                                result.model_dump(), request.version
                            )
                except Exception as e:
                    errors.append(f"Export failed for {fmt.value}: {e}")
                    logger.exception("Export failed for %s", fmt.value)

        try:
            schema_files = self.schema_exporter.export(
                document, output_dir, base_url, extra_schema_data
            )
            export_files.extend(schema_files)
        except Exception as e:
            errors.append(f"Schema export failed: {e}")

        if request.include_manifest:
            try:
                self.manifest_generator.generate(
                    request.project_id, request.export_id, request.version,
                    document.title, export_files, output_dir,
                    statistics=self._compute_statistics(document, export_files, start_time),
                )
            except Exception as e:
                errors.append(f"Manifest generation failed: {e}")

        if request.include_package:
            try:
                package = self.package_builder.build_package(
                    output_dir, request.export_id, request.version,
                    export_files, self.manifest_generator.generate(
                        request.project_id, request.export_id, request.version,
                        document.title, export_files, output_dir,
                    )
                )
            except Exception as e:
                errors.append(f"Package build failed: {e}")

        if request.run_validation:
            validation_results = self.validator.validate_document(document)
            for f in export_files:
                fpath = output_dir / f.filename
                if fpath.exists():
                    validation_results.extend(
                        self.validator.validate_export_file(fpath, f.format)
                    )

        try:
            self.version_manager.save(
                request.project_id, request.version,
                [f.model_dump() for f in export_files],
                {"title": document.title, "export_id": request.export_id},
            )
        except Exception as e:
            errors.append(f"Version saving failed: {e}")

        elapsed_ms = int((time.time() - start_time) * 1000)

        return ExportResult(
            export_id=request.export_id,
            project_id=request.project_id,
            version=request.version,
            title=document.title,
            formats=list(set(f.format for f in export_files)),
            files=export_files,
            total_files=len(export_files),
            total_size_bytes=sum(f.size_bytes for f in export_files),
            total_size_display=self._size_display(
                sum(f.size_bytes for f in export_files)
            ),
            output_dir=str(output_dir),
            execution_time_ms=elapsed_ms,
            success=len(errors) == 0,
            errors=errors,
            validation_results=validation_results,
        )

    def _export_single(self, exporter: Any, document: DocumentModel,
                       fmt: ExportFormat, output_dir: Path,
                       base_url: str, project_data: dict[str, Any] | None = None
                       ) -> ExportFileInfo:
        if fmt == ExportFormat.JSON:
            extra = {}
            if project_data:
                extra["project_metadata"] = project_data
            return exporter.export(document, output_dir, extra=extra, base_url=base_url)
        return exporter.export(document, output_dir, base_url=base_url)

    def _resolve_formats(self, request: ExportRequest) -> list[ExportFormat]:
        if request.formats:
            return list(set(request.formats))
        return [
            ExportFormat.MARKDOWN, ExportFormat.HTML, ExportFormat.DOCX,
            ExportFormat.PDF, ExportFormat.TXT, ExportFormat.JSON,
        ]

    def _compute_statistics(self, document: DocumentModel,
                            files: list[ExportFileInfo],
                            start_time: float) -> dict[str, Any]:
        return {
            "word_count": document.word_count,
            "section_count": len(document.sections),
            "image_count": document.image_count,
            "table_count": len(document.tables),
            "code_block_count": len(document.code_blocks),
            "link_count": len(document.links),
            "heading_count": len(document.headings),
            "faq_count": len(document.faq),
            "reading_time_minutes": document.reading_time_minutes,
            "file_count": len(files),
            "total_size_bytes": sum(f.size_bytes for f in files),
            "execution_time_ms": int((time.time() - start_time) * 1000),
        }

    @staticmethod
    def _size_display(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
