"""Document Builder — orchestrates section assembly into a complete document.

Coordinates section merging, heading normalization, TOC generation,
reference resolution, and Markdown building into a single pipeline.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from draft.draft_models import (
    AssemblyConfig,
    DiscoveredSection,
    DraftDocument,
    MergeLogEntry,
    MergeStatus,
    SectionValidationResult,
    TableOfContentsEntry,
    utc_now,
    compute_checksum,
)
from draft.section_merger import SectionMerger
from draft.heading_normalizer import HeadingNormalizer
from draft.toc_generator import TOCGenerator
from draft.reference_resolver import ReferenceResolver
from draft.markdown_builder import MarkdownBuilder
from draft.document_validator import DocumentValidator

logger = logging.getLogger(__name__)


class DocumentBuilder:
    """Orchestrates the assembly of sections into a complete draft document."""

    def __init__(self) -> None:
        self._section_merger = SectionMerger()
        self._heading_normalizer = HeadingNormalizer()
        self._toc_generator = TOCGenerator()
        self._reference_resolver = ReferenceResolver()
        self._markdown_builder = MarkdownBuilder()
        self._document_validator = DocumentValidator()

    @property
    def section_merger(self) -> SectionMerger:
        return self._section_merger

    def assemble(
        self,
        sections_path: Path | None = None,
        sections_data: list[dict[str, Any]] | None = None,
        title: str = "",
        seo_title: str = "",
        meta_description: str = "",
        config: AssemblyConfig | None = None,
    ) -> DraftDocument:
        config = config or AssemblyConfig()
        start_time = time.time()

        if sections_path:
            discovered = self._section_merger.discover_sections(sections_path)
        elif sections_data:
            discovered = self._section_merger.discover_from_list(sections_data)
        else:
            discovered = []
        if not discovered:
            logger.warning("No sections discovered for assembly")
            return DraftDocument(title=title or seo_title or "Untitled")

        discovered = self._section_merger.sort_by_order(discovered)

        if config.normalize_headings:
            discovered = self._heading_normalizer.normalize(discovered)

        validation_results = self._document_validator.validate_document(
            discovered, config.model_dump() if hasattr(config, "model_dump") else {},
        )

        has_critical = self._document_validator.has_critical_failures(validation_results)
        if has_critical and config.fail_on_validation_error:
            raise ValueError("Critical validation failures detected, aborting assembly")

        toc_markdown = ""

        if config.generate_toc:
            toc = self._toc_generator.generate(discovered, title or seo_title)
            toc_markdown = self._toc_generator.generate_markdown(toc)
        else:
            toc = []

        document_content = self._markdown_builder.build_document(
            title=title or seo_title or "Blog Post",
            sections=discovered,
            toc_markdown=toc_markdown,
            seo_title=seo_title,
            meta_description=meta_description,
            add_horizontal_rules=config.add_horizontal_rules,
            add_metadata_header=config.add_metadata_header,
        )

        if config.normalize_headings:
            document_content = self._heading_normalizer.ensure_title_h1(
                document_content, title or seo_title or "Blog Post",
            )
            document_content = self._heading_normalizer.normalize_heading_spacing(
                document_content,
            )

        if config.resolve_references:
            document_content = self._reference_resolver.resolve_all(
                document_content, discovered,
            )

        word_count = len(document_content.split())
        reading_time = self._document_validator.estimate_reading_time_minutes(word_count)
        heading_count = self._document_validator.count_headings(document_content)
        paragraph_count = self._document_validator.count_paragraphs(document_content)
        image_count = self._document_validator.count_images(document_content)
        table_count = self._document_validator.count_tables(document_content)
        code_block_count = self._document_validator.count_code_blocks(document_content)
        blockquote_count = self._document_validator.count_blockquotes(document_content)
        list_count = self._document_validator.count_lists(document_content)

        document = DraftDocument(
            title=title or seo_title or "Blog Post",
            seo_title=seo_title,
            meta_description=meta_description,
            content=document_content,
            sections=discovered,
            toc=toc if config.generate_toc else [],
            word_count=word_count,
            reading_time_minutes=reading_time,
            section_count=len(discovered),
            heading_count=heading_count,
            paragraph_count=paragraph_count,
            image_count=image_count,
            table_count=table_count,
            code_block_count=code_block_count,
            blockquote_count=blockquote_count,
            list_count=list_count,
        )

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            "Assembled %d sections into draft (%d words) in %.0fms",
            len(discovered), word_count, elapsed_ms,
        )

        return document

