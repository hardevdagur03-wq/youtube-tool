"""Section Metadata Generator — creates and manages metadata per section.

Tracks section ID, heading, order, word count, reading time,
keywords used, entities used, facts used, version, generation time,
validation score, and status.
"""

from __future__ import annotations

import logging
from typing import Any

from section_generation.section_models import (
    SectionMetadata,
    SectionManifest,
    SectionOutput,
    SectionStatus,
    SectionType,
    utc_now,
    estimate_reading_time_seconds,
)

logger = logging.getLogger(__name__)


class SectionMetadataGenerator:
    """Creates and manages metadata for generated sections."""

    def create_metadata(self, output: SectionOutput) -> SectionMetadata:
        return SectionMetadata(
            section_id=output.section_id,
            section_type=output.section_type,
            heading=output.heading,
            order=output.order,
            word_count=output.word_count,
            reading_time_seconds=estimate_reading_time_seconds(output.word_count),
            keywords_used=output.keywords_used,
            entities_used=output.entities_used,
            facts_used=output.facts_used,
            version=output.version,
            generation_time_ms=output.generation_time_ms,
            validation_score=0.0,
            status=output.status,
            created_at=utc_now(),
            updated_at=utc_now(),
        )

    def update_manifest(
        self,
        manifest: SectionManifest,
        metadata: SectionMetadata,
    ) -> SectionManifest:
        manifest.sections[metadata.section_id] = metadata
        manifest.total_sections = len(manifest.sections)
        manifest.completed_sections = sum(
            1 for s in manifest.sections.values()
            if s.status in (SectionStatus.COMPLETED, SectionStatus.CACHED)
        )
        manifest.failed_sections = sum(
            1 for s in manifest.sections.values()
            if s.status == SectionStatus.FAILED
        )
        manifest.pending_sections = sum(
            1 for s in manifest.sections.values()
            if s.status == SectionStatus.PENDING
        )
        manifest.overall_progress_pct = round(
            manifest.completed_sections / max(manifest.total_sections, 1) * 100, 1
        )
        manifest.updated_at = utc_now()
        return manifest

    def create_manifest(self, project_id: str) -> SectionManifest:
        return SectionManifest(
            project_id=project_id,
            created_at=utc_now(),
            updated_at=utc_now(),
        )

    def update_validation_score(
        self,
        metadata: SectionMetadata,
        score: float,
    ) -> SectionMetadata:
        metadata.validation_score = round(score, 1)
        metadata.updated_at = utc_now()
        return metadata

    def update_status(
        self,
        metadata: SectionMetadata,
        status: SectionStatus,
    ) -> SectionMetadata:
        metadata.status = status
        metadata.updated_at = utc_now()
        return metadata
