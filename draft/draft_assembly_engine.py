"""Draft Assembly Engine — enterprise-grade document assembly pipeline.

This is the main entry point for the Draft Assembly Engine.
It orchestrates section discovery, validation, normalization,
assembly, versioning, and storage into a single pipeline.

No content generation occurs here — only intelligent assembly.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

from draft.draft_models import (
    AssemblyConfig,
    DiscoveredSection,
    DraftDocument,
    DraftMetadata,
    DraftVersion,
    MergeLogEntry,
    MergeStatus,
    SectionValidationResult,
    utc_now,
    compute_checksum,
)
from draft.draft_storage import DraftStorage, DraftStorageError
from draft.document_builder import DocumentBuilder
from draft.document_validator import DocumentValidator
from draft.version_manager import DraftVersionManager
from draft.section_merger import SectionMerger

logger = logging.getLogger(__name__)


class DraftAssemblyEngine:
    """Main entry point for the Draft Assembly Engine.

    Coordinates the end-to-end assembly pipeline:
    1. Load configuration and discover inputs
    2. Discover and validate sections
    3. Normalize headings
    4. Generate table of contents
    5. Resolve references
    6. Build markdown document
    7. Version the draft
    8. Store artifacts
    9. Log merge results
    """

    def __init__(
        self,
        storage: DraftStorage | None = None,
        document_builder: DocumentBuilder | None = None,
        version_manager: DraftVersionManager | None = None,
    ) -> None:
        self._storage = storage or DraftStorage()
        self._builder = document_builder or DocumentBuilder()
        self._version_mgr = version_manager or DraftVersionManager(self._storage)
        self._validator = DocumentValidator()
        self._section_merger = SectionMerger()

    @property
    def storage(self) -> DraftStorage:
        return self._storage

    @property
    def builder(self) -> DocumentBuilder:
        return self._builder

    @property
    def version_manager(self) -> DraftVersionManager:
        return self._version_mgr

    def assemble(
        self,
        project_id: str,
        title: str = "",
        seo_title: str = "",
        meta_description: str = "",
        sections_path: Path | None = None,
        sections_data: list[dict[str, Any]] | None = None,
        outline_data: dict[str, Any] | None = None,
        seo_data: dict[str, Any] | None = None,
        config: AssemblyConfig | None = None,
    ) -> DraftDocument:
        config = config or AssemblyConfig()
        start_time = time.time()
        warnings: list[str] = []
        errors: list[str] = []
        validation_results: dict[str, SectionValidationResult] = {}

        if not title and outline_data:
            title = self._extract_title(outline_data)
        if not seo_title and seo_data:
            seo_title = self._extract_seo_title(seo_data)

        discovered_sections = self._builder.section_merger.discover_sections(
            sections_path,
        ) if sections_path else (self._builder.section_merger.discover_from_list(
            sections_data or [],
        ) if sections_data else [])

        if not discovered_sections:
            errors.append("No sections discovered for assembly")
            logger.error("No sections discovered for project %s", project_id)

        complete, missing_types = self._section_merger.check_completeness(
            discovered_sections,
        )
        if not complete:
            warnings.append(f"Missing section types: {', '.join(missing_types)}")
            if config.fail_on_missing_section:
                errors.append(f"Critical: missing required sections: {missing_types}")
                raise ValueError(f"Missing required sections: {missing_types}")

        for section in discovered_sections:
            vresult = self._validator.validate_section(
                section, config.model_dump() if hasattr(config, "model_dump") else {},
            )
            validation_results[section.section_id] = vresult

        if config.fail_on_validation_error:
            critical = self._validator.has_critical_failures(
                list(validation_results.values()),
            )
            if critical:
                errors.append("Critical validation failures detected")

        self._validate_section_ordering(discovered_sections, warnings)

        document = self._builder.assemble(
            sections_path=sections_path,
            sections_data=sections_data,
            title=title,
            seo_title=seo_title,
            meta_description=meta_description,
            config=config,
        )

        document_content = document.content

        checksum = compute_checksum(document_content)

        existing_content = self._storage.load_draft(project_id)
        if existing_content and compute_checksum(existing_content) == checksum:
            logger.info("Draft unchanged for project %s, skipping storage", project_id)
            metadata = self._storage.load_metadata(project_id)
            if metadata:
                metadata.updated_at = utc_now()
                metadata.status = MergeStatus.CACHED
                self._storage.save_metadata(project_id, metadata)
                document.content = existing_content
                return document

        version = self._version_mgr.create_version(
            project_id, document,
            modified_sections=[s.section_id for s in document.sections],
        )

        self._storage.save_draft(project_id, document, version.version_number)

        metadata = DraftMetadata(
            project_id=project_id,
            draft_version=version.version_number,
            status=MergeStatus.COMPLETED,
            created_at=version.created_at,
            updated_at=utc_now(),
            seo_score=self._extract_seo_score(seo_data),
            total_word_count=document.word_count,
            reading_time_minutes=document.reading_time_minutes,
            section_count=document.section_count,
            heading_count=document.heading_count,
            paragraph_count=document.paragraph_count,
            image_count=document.image_count,
            table_count=document.table_count,
            code_block_count=document.code_block_count,
            blockquote_count=document.blockquote_count,
            list_count=document.list_count,
        )

        if errors:
            metadata.status = MergeStatus.FAILED
        elif warnings:
            metadata.status = MergeStatus.PARTIAL

        self._storage.save_metadata(project_id, metadata)

        elapsed_ms = (time.time() - start_time) * 1000
        merge_log = MergeLogEntry(
            merge_id=version.content_hash[:16],
            timestamp=utc_now(),
            version=version.version_number,
            status=MergeStatus.COMPLETED if not errors else MergeStatus.PARTIAL,
            sections_merged=[s.section_id for s in document.sections],
            section_count=document.section_count,
            word_count=document.word_count,
            checksum=checksum,
            warnings=warnings,
            errors=errors,
            elapsed_ms=round(elapsed_ms, 2),
            validation_results=validation_results,
        )
        self._storage.save_merge_log(project_id, merge_log)

        logger.info(
            "Draft assembly complete for project %s: v%d, %d sections, %d words, %.0fms",
            project_id, version.version_number, document.section_count,
            document.word_count, elapsed_ms,
        )

        return document

    def _validate_section_ordering(
        self,
        sections: list[DiscoveredSection],
        warnings: list[str],
    ) -> None:
        type_order = {
            "introduction": 0,
            "body": 1,
            "faq": 2,
            "conclusion": 3,
            "cta": 4,
        }
        for i in range(len(sections) - 1):
            curr = type_order.get(sections[i].section_type.value, 5)
            next_type = type_order.get(sections[i + 1].section_type.value, 5)
            if curr > next_type:
                warnings.append(
                    f"Section ordering issue: {sections[i].filename} "
                    f"({sections[i].section_type.value}) before "
                    f"{sections[i+1].filename} ({sections[i+1].section_type.value})"
                )

    def _extract_title(self, outline_data: dict[str, Any]) -> str:
        title_obj = outline_data.get("title", {})
        if isinstance(title_obj, dict):
            return title_obj.get("primary_title", "") or title_obj.get("seo_title", "")
        if isinstance(title_obj, str):
            return title_obj
        return ""

    def _extract_seo_title(self, seo_data: dict[str, Any]) -> str:
        meta = seo_data.get("meta", {})
        if isinstance(meta, dict):
            return meta.get("meta_title", "")
        seo_title = seo_data.get("seo_title", "")
        return seo_title if isinstance(seo_title, str) else ""

    def _extract_seo_score(self, seo_data: dict[str, Any] | None) -> float:
        if not seo_data:
            return 0.0
        return float(seo_data.get("seo_score", seo_data.get("score", 0.0)))

    def get_draft(self, project_id: str, version: int | None = None) -> str | None:
        return self._storage.load_draft(project_id, version)

    def get_latest_draft(self, project_id: str) -> str | None:
        return self._storage.load_draft(project_id)

    def get_metadata(self, project_id: str) -> DraftMetadata | None:
        return self._storage.load_metadata(project_id)

    def get_merge_log(self, project_id: str) -> list[MergeLogEntry]:
        return self._storage.load_merge_log(project_id)

    def get_versions(self, project_id: str) -> list[DraftVersion]:
        return self._version_mgr.get_versions(project_id)

    def list_draft_versions(self, project_id: str) -> list[int]:
        return self._storage.list_draft_versions(project_id)

    def rollback(self, project_id: str, target_version: int) -> str | None:
        return self._version_mgr.rollback(project_id, target_version)

    def prune_versions(self, project_id: str, keep: int = 10) -> int:
        return self._version_mgr.prune_versions(project_id, keep)

    def draft_exists(self, project_id: str, version: int | None = None) -> bool:
        return self._storage.draft_exists(project_id, version)

    def has_changes(
        self,
        project_id: str,
        sections: list[DiscoveredSection],
    ) -> bool:
        existing = self._storage.load_draft(project_id)
        if not existing:
            return True
        combined = "\n\n".join(s.content for s in sections)
        return compute_checksum(existing) != compute_checksum(
            self._builder.assemble(
                sections_data=[{"content": s.content, "heading": s.heading,
                                "section_id": s.section_id, "type": s.section_type.value,
                                "order": s.order} for s in sections],
            ).content,
        )

    def compute_statistics(self, project_id: str) -> dict[str, Any]:
        metadata = self._storage.load_metadata(project_id)
        versions = self._version_mgr.get_versions(project_id)
        log = self._storage.load_merge_log(project_id)
        return {
            "draft_version": metadata.draft_version if metadata else 0,
            "total_versions": len(versions),
            "total_merges": len(log),
            "word_count": metadata.total_word_count if metadata else 0,
            "reading_time_minutes": metadata.reading_time_minutes if metadata else 0,
            "section_count": metadata.section_count if metadata else 0,
            "storage_bytes": self._storage.get_storage_usage(project_id),
            "status": metadata.status.value if metadata else "none",
        }
