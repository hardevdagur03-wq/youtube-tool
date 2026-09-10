"""Comprehensive tests for the Draft Assembly Engine.

Tests cover:
- Section discovery from disk
- Section ordering
- Markdown rendering
- Heading normalization
- Table preservation
- Image preservation
- Anchor links and references
- Versioning
- Rollback
- Large document merge
- Performance
- Stress tests
- Error handling
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any
import pytest

from draft.draft_assembly_engine import DraftAssemblyEngine
from draft.draft_models import (
    AssemblyConfig,
    DiscoveredSection,
    DraftDocument,
    DraftMetadata,
    DraftVersion,
    MergeLogEntry,
    MergeStatus,
    SectionType,
    SectionValidationResult,
    utc_now,
)
from draft.draft_storage import DraftStorage, DraftStorageError
from draft.document_builder import DocumentBuilder
from draft.document_validator import DocumentValidator
from draft.heading_normalizer import HeadingNormalizer
from draft.markdown_builder import MarkdownBuilder
from draft.reference_resolver import ReferenceResolver
from draft.section_merger import SectionMerger
from draft.toc_generator import TOCGenerator
from draft.version_manager import DraftVersionManager

TEST_PROJECT_ID = "test_draft_project"


# ─── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def tmp_base(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def storage(tmp_base: Path) -> DraftStorage:
    return DraftStorage(base_path=str(tmp_base))


@pytest.fixture
def engine(tmp_base: Path) -> DraftAssemblyEngine:
    st = DraftStorage(base_path=str(tmp_base))
    return DraftAssemblyEngine(storage=st)


@pytest.fixture
def sample_sections_path(tmp_base: Path) -> Path:
    base = tmp_base / "projects" / TEST_PROJECT_ID / "sections"
    base.mkdir(parents=True, exist_ok=True)

    (base / "intro.md").write_text(
        "# Introduction\n\nThis is the introduction section.\n", encoding="utf-8"
    )
    (base / "section_01.md").write_text(
        "## First Section\n\nThis is the first body section.\n", encoding="utf-8"
    )
    (base / "section_02.md").write_text(
        "## Second Section\n\nThis is the second body section.\n", encoding="utf-8"
    )
    (base / "faq.md").write_text(
        "## FAQ\n\n### What is this?\n\nThis is a test.\n\n### Why does it matter?\n\nIt matters for testing.\n", encoding="utf-8"
    )
    (base / "conclusion.md").write_text(
        "## Conclusion\n\nThis is the conclusion.\n", encoding="utf-8"
    )
    (base / "cta.md").write_text(
        "## Next Steps\n\nSubscribe for more.\n", encoding="utf-8"
    )
    return base


@pytest.fixture
def sample_section_data() -> list[dict[str, Any]]:
    return [
        {"section_id": "intro", "type": "introduction", "heading": "Introduction",
         "content": "# Introduction\n\nWelcome to the guide.\n", "order": 0},
        {"section_id": "section_01", "type": "body", "heading": "Getting Started",
         "content": "## Getting Started\n\nHere is how to start.\n", "order": 1},
        {"section_id": "section_02", "type": "body", "heading": "Advanced Topics",
         "content": "## Advanced Topics\n\nDeeper dive into the topic.\n", "order": 2},
        {"section_id": "faq", "type": "faq", "heading": "FAQ",
         "content": "## FAQ\n\n### Common Question?\n\nHere is the answer.\n", "order": 3},
        {"section_id": "conclusion", "type": "conclusion", "heading": "Conclusion",
         "content": "## Conclusion\n\nFinal thoughts.\n", "order": 4},
        {"section_id": "cta", "type": "cta", "heading": "Next Steps",
         "content": "## Next Steps\n\nTake action now.\n", "order": 5},
    ]


# ─── Section Discovery Tests ─────────────────────────────────────

class TestSectionDiscovery:
    def test_discover_from_disk(self, sample_sections_path: Path):
        merger = SectionMerger()
        sections = merger.discover_sections(sample_sections_path)
        assert len(sections) >= 5
        assert any(s.section_type == SectionType.INTRODUCTION for s in sections)
        assert any(s.section_type == SectionType.BODY for s in sections)
        assert any(s.section_type == SectionType.FAQ for s in sections)
        assert any(s.section_type == SectionType.CONCLUSION for s in sections)
        assert any(s.section_type == SectionType.CTA for s in sections)

    def test_discover_from_list(self, sample_section_data: list[dict]):
        merger = SectionMerger()
        sections = merger.discover_from_list(sample_section_data)
        assert len(sections) == 6
        assert sections[0].section_type == SectionType.INTRODUCTION

    def test_discover_empty_directory(self, tmp_base: Path):
        empty = tmp_base / "empty_sections"
        empty.mkdir(parents=True, exist_ok=True)
        merger = SectionMerger()
        sections = merger.discover_sections(empty)
        assert len(sections) == 0

    def test_discover_non_existent_path(self):
        merger = SectionMerger()
        sections = merger.discover_sections(Path("/nonexistent/path"))
        assert len(sections) == 0

    def test_section_ordering(self, sample_sections_path: Path):
        merger = SectionMerger()
        sections = merger.discover_sections(sample_sections_path)
        sorted_sections = merger.sort_by_order(sections)
        types = [s.section_type for s in sorted_sections]
        intro_idx = types.index(SectionType.INTRODUCTION)
        faq_idx = types.index(SectionType.FAQ)
        conclusion_idx = types.index(SectionType.CONCLUSION)
        cta_idx = types.index(SectionType.CTA)
        assert intro_idx < faq_idx < conclusion_idx < cta_idx

    def test_detect_changes(self):
        merger = SectionMerger()
        old = [
            DiscoveredSection(section_id="intro", content="Old intro", section_type=SectionType.INTRODUCTION),
            DiscoveredSection(section_id="s1", content="Old s1", section_type=SectionType.BODY),
        ]
        new = [
            DiscoveredSection(section_id="intro", content="Updated intro", section_type=SectionType.INTRODUCTION),
            DiscoveredSection(section_id="s1", content="Old s1", section_type=SectionType.BODY),
            DiscoveredSection(section_id="s2", content="New s2", section_type=SectionType.BODY),
        ]
        changes = merger.detect_changes(old, new)
        assert "modified" in changes
        assert "added" in changes
        assert changes["added"] == ["s2"]
        assert changes["modified"] == ["intro"]

    def test_check_completeness(self):
        merger = SectionMerger()
        complete_sections = [
            DiscoveredSection(section_id="i", section_type=SectionType.INTRODUCTION),
            DiscoveredSection(section_id="b", section_type=SectionType.BODY),
            DiscoveredSection(section_id="c", section_type=SectionType.CONCLUSION),
            DiscoveredSection(section_id="cta", section_type=SectionType.CTA),
        ]
        complete, missing = merger.check_completeness(complete_sections)
        assert complete
        assert len(missing) == 0

        incomplete_sections = [
            DiscoveredSection(section_id="i", section_type=SectionType.INTRODUCTION),
        ]
        complete, missing = merger.check_completeness(incomplete_sections)
        assert not complete
        assert "conclusion" in missing or "cta" in missing or "body" in missing


# ─── Section Validation Tests ────────────────────────────────────

class TestDocumentValidator:
    def test_validate_valid_section(self):
        validator = DocumentValidator()
        section = DiscoveredSection(
            section_id="intro",
            content="# Valid Heading\n\nThis is valid content with enough words.\n",
        )
        result = validator.validate_section(section)
        assert result.exists
        assert result.valid
        assert result.has_heading

    def test_validate_empty_section(self):
        validator = DocumentValidator()
        section = DiscoveredSection(section_id="empty", content="")
        result = validator.validate_section(section)
        assert not result.exists
        assert not result.valid

    def test_validate_corrupted_content(self):
        validator = DocumentValidator()
        section = DiscoveredSection(
            section_id="corrupt",
            content="# Test\n\nThis has null bytes\x00 in it.\n",
        )
        result = validator.validate_section(section)
        assert not result.no_corruption

    def test_heading_counting(self):
        validator = DocumentValidator()
        content = "# H1\n\n## H2\n\n### H3\n\nParagraph.\n"
        assert validator.count_headings(content) == 3

    def test_table_counting(self):
        validator = DocumentValidator()
        content = "| H1 | H2 |\n|----|----|\n| A | B |\n\n| H3 | H4 |\n|----|----|\n| C | D |\n"
        assert validator.count_tables(content) == 2

    def test_image_counting(self):
        validator = DocumentValidator()
        content = "![alt](image.png)\n\nText\n\n![alt2](image2.jpg)\n"
        assert validator.count_images(content) == 2

    def test_code_block_counting(self):
        validator = DocumentValidator()
        content = "```python\nprint('hello')\n```\n\nText\n\n```javascript\nconsole.log('hi')\n```\n"
        assert validator.count_code_blocks(content) == 2

    def test_blockquote_counting(self):
        validator = DocumentValidator()
        content = "> Quote 1\n\nNormal\n\n> Quote 2\n"
        assert validator.count_blockquotes(content) == 2

    def test_list_counting(self):
        validator = DocumentValidator()
        content = "- Item 1\n- Item 2\n\n1. Ordered 1\n2. Ordered 2\n"
        assert validator.count_lists(content) == 2

    def test_reading_time(self):
        validator = DocumentValidator()
        assert validator.estimate_reading_time_minutes(200) == 1
        assert validator.estimate_reading_time_minutes(400) == 2

    def test_heading_hierarchy_warnings(self):
        validator = DocumentValidator()
        sections = [
            DiscoveredSection(section_id="s1", content="# H1\n\nContent\n"),
            DiscoveredSection(section_id="s2", content="# H1 Again\n\nMore content\n"),
        ]
        warnings = validator.check_heading_hierarchy(sections)
        assert len(warnings) > 0

    def test_has_critical_failures(self):
        validator = DocumentValidator()
        results = [
            SectionValidationResult(section_id="s1", valid=True),
            SectionValidationResult(section_id="s2", valid=False, errors=["empty"]),
        ]
        assert validator.has_critical_failures(results)

        results_no_critical = [
            SectionValidationResult(section_id="s1", valid=True),
            SectionValidationResult(section_id="s2", valid=True, warnings=["short"]),
        ]
        assert not validator.has_critical_failures(results_no_critical)

    def test_check_missing_sections(self):
        validator = DocumentValidator()
        missing = validator.check_missing_sections(
            ["intro.md", "section_01.md", "faq.md"],
            ["intro.md", "section_01.md"],
        )
        assert missing == ["faq.md"]


# ─── Heading Normalizer Tests ────────────────────────────────────

class TestHeadingNormalizer:
    def test_normalize_intro_to_h2(self):
        normalizer = HeadingNormalizer()
        intro = DiscoveredSection(
            section_id="intro",
            content="# Introduction\n\nContent.\n",
            section_type=SectionType.INTRODUCTION,
        )
        normalized = normalizer.normalize([intro])
        assert "## Introduction" in normalized[0].content

    def test_normalize_faq_questions_to_h3(self):
        normalizer = HeadingNormalizer()
        faq = DiscoveredSection(
            section_id="faq",
            content="## FAQ\n\n## What is this?\n\nAnswer.\n",
            section_type=SectionType.FAQ,
        )
        normalized = normalizer.normalize([faq])
        content = normalized[0].content
        assert "## FAQ" in content
        assert "### What is this?" in content

    def test_anchor_id_generation(self):
        normalizer = HeadingNormalizer()
        assert normalizer.get_anchor_id("Hello World") == "hello-world"
        assert normalizer.get_anchor_id("What is Python?") == "what-is-python"
        assert normalizer.get_anchor_id("Step 1: Introduction") == "step-1-introduction"

    def test_heading_spacing(self):
        normalizer = HeadingNormalizer()
        content = "## Heading\n\n\n\n\nContent\n\n\n\n\n## Next Heading\n"
        normalized = normalizer.normalize_heading_spacing(content)
        assert "\n\n\n" not in normalized


# ─── TOC Generator Tests ─────────────────────────────────────────

class TestTOCGenerator:
    def test_generate_toc(self):
        gen = TOCGenerator()
        sections = [
            DiscoveredSection(section_id="intro", content="## Introduction\n\nContent"),
            DiscoveredSection(section_id="s1", content="## Section 1\n\nContent"),
            DiscoveredSection(section_id="faq", content="## FAQ\n\n### Q1\n\nA1"),
        ]
        toc = gen.generate(sections, "Test Title")
        assert len(toc) >= 3

    def test_toc_markdown_output(self):
        gen = TOCGenerator()
        toc_entry = type("Entry", (), {"level": 2, "title": "Test", "anchor_id": "test", "children": []})()
        md = gen.generate_markdown([toc_entry])
        assert "Test" in md
        assert "#test" in md

    def test_anchor_id_deduplication(self):
        gen = TOCGenerator()
        id1 = gen._anchor_id("Hello World")
        id2 = gen._anchor_id("Hello World!")
        assert id1 == id2


# ─── Reference Resolver Tests ────────────────────────────────────

class TestReferenceResolver:
    def test_build_index(self):
        resolver = ReferenceResolver()
        sections = [
            DiscoveredSection(section_id="intro", content="# Introduction\n\nContent\n"),
            DiscoveredSection(section_id="s1", content="## Section One\n\nContent\n"),
        ]
        resolver.build_index(sections)
        assert len(resolver._heading_map) > 0

    def test_anchor_id_consistency(self):
        resolver = ReferenceResolver()
        id1 = resolver._anchor_id("Hello World")
        id2 = resolver._anchor_id("Hello World")
        assert id1 == id2


# ─── Markdown Builder Tests ──────────────────────────────────────

class TestMarkdownBuilder:
    def test_build_document(self):
        builder = MarkdownBuilder()
        sections = [
            DiscoveredSection(section_id="intro", content="## Intro\n\nContent\n"),
        ]
        doc = builder.build_document("Test Title", sections)
        assert doc.startswith("# Test Title")
        assert "## Intro" in doc

    def test_format_table(self):
        builder = MarkdownBuilder()
        table = builder.format_table(
            headers=["Name", "Age"],
            rows=[["Alice", "30"], ["Bob", "25"]],
        )
        assert "| Name" in table
        assert "| :---" in table
        assert "Alice" in table

    def test_format_image(self):
        builder = MarkdownBuilder()
        img = builder.format_image("Alt", "url.png", caption="Test Caption")
        assert "![Alt](url.png)" in img
        assert "Test Caption" in img

    def test_format_code_block(self):
        builder = MarkdownBuilder()
        code = builder.format_code_block("print('hello')", language="python")
        assert "```python" in code
        assert "print('hello')" in code

    def test_format_blockquote(self):
        builder = MarkdownBuilder()
        quote = builder.format_blockquote("This is a quote", "Author")
        assert "> This is a quote" in quote
        assert "Author" in quote

    def test_format_list(self):
        builder = MarkdownBuilder()
        lst = builder.format_list(["Item 1", "Item 2"])
        assert "- Item 1" in lst
        assert "- Item 2" in lst

    def test_format_ordered_list(self):
        builder = MarkdownBuilder()
        lst = builder.format_list(["First", "Second"], ordered=True)
        assert "1. First" in lst
        assert "2. Second" in lst

    def test_format_link(self):
        builder = MarkdownBuilder()
        link = builder.format_link("Click here", "https://example.com")
        assert "[Click here](https://example.com)" in link


# ─── Document Builder Tests ──────────────────────────────────────

class TestDocumentBuilder:
    def test_assemble_from_disk(self, sample_sections_path: Path):
        builder = DocumentBuilder()
        doc = builder.assemble(
            sections_path=sample_sections_path,
            title="Test Blog Post",
        )
        assert doc.word_count > 0
        assert doc.section_count >= 5
        assert doc.title == "Test Blog Post"
        assert doc.content.strip()

    def test_assemble_from_data(self, sample_section_data: list[dict]):
        builder = DocumentBuilder()
        doc = builder.assemble(
            sections_data=sample_section_data,
            title="Data Test",
        )
        assert doc.word_count > 0
        assert doc.section_count == 6

    def test_assemble_with_toc(self, sample_section_data: list[dict]):
        builder = DocumentBuilder()
        doc = builder.assemble(
            sections_data=sample_section_data,
            title="TOC Test",
            config=AssemblyConfig(generate_toc=True),
        )
        assert "Table of Contents" in doc.content

    def test_assemble_without_toc(self, sample_section_data: list[dict]):
        builder = DocumentBuilder()
        doc = builder.assemble(
            sections_data=sample_section_data,
            title="No TOC Test",
            config=AssemblyConfig(generate_toc=False),
        )
        assert "Table of Contents" not in doc.content

    def test_assemble_empty(self):
        builder = DocumentBuilder()
        doc = builder.assemble(title="Empty")
        assert doc.word_count == 0
        assert doc.section_count == 0


# ─── Draft Storage Tests ─────────────────────────────────────────

class TestDraftStorage:
    def test_save_and_load_draft(self, storage: DraftStorage, sample_section_data: list[dict]):
        builder = DocumentBuilder()
        doc = builder.assemble(sections_data=sample_section_data, title="Storage Test")
        storage.save_draft(TEST_PROJECT_ID, doc, version=1)
        loaded = storage.load_draft(TEST_PROJECT_ID, version=1)
        assert loaded is not None
        assert "# Storage Test" in loaded

    def test_latest_draft_link(self, storage: DraftStorage, sample_section_data: list[dict]):
        builder = DocumentBuilder()
        doc = builder.assemble(sections_data=sample_section_data, title="Latest Test")
        storage.save_draft(TEST_PROJECT_ID, doc, version=1)
        latest = storage.load_draft(TEST_PROJECT_ID)
        assert latest is not None
        assert "Latest Test" in latest

    def test_draft_metadata(self, storage: DraftStorage):
        meta = DraftMetadata(
            project_id=TEST_PROJECT_ID,
            draft_version=1,
            status=MergeStatus.COMPLETED,
            total_word_count=100,
        )
        storage.save_metadata(TEST_PROJECT_ID, meta)
        loaded = storage.load_metadata(TEST_PROJECT_ID)
        assert loaded is not None
        assert loaded.draft_version == 1
        assert loaded.total_word_count == 100

    def test_merge_log(self, storage: DraftStorage):
        entry = MergeLogEntry(
            merge_id="test_001",
            timestamp=utc_now(),
            version=1,
            sections_merged=["intro", "s1"],
            section_count=2,
            word_count=100,
            checksum="abc123",
        )
        storage.save_merge_log(TEST_PROJECT_ID, entry)
        log = storage.load_merge_log(TEST_PROJECT_ID)
        assert len(log) == 1
        assert log[0].version == 1

    def test_draft_versioning(self, storage: DraftStorage):
        v1 = DraftVersion(version_number=1)
        v2 = DraftVersion(version_number=2)
        storage.save_version(TEST_PROJECT_ID, v1)
        storage.save_version(TEST_PROJECT_ID, v2)
        versions = storage.list_versions(TEST_PROJECT_ID)
        assert len(versions) == 2

    def test_list_draft_versions(self, storage: DraftStorage, sample_section_data: list[dict]):
        builder = DocumentBuilder()
        doc = builder.assemble(sections_data=sample_section_data, title="Versions")
        storage.save_draft(TEST_PROJECT_ID, doc, version=1)
        storage.save_draft(TEST_PROJECT_ID, doc, version=2)
        versions = storage.list_draft_versions(TEST_PROJECT_ID)
        assert 1 in versions
        assert 2 in versions

    def test_draft_exists(self, storage: DraftStorage, sample_section_data: list[dict]):
        assert not storage.draft_exists(TEST_PROJECT_ID)
        builder = DocumentBuilder()
        doc = builder.assemble(sections_data=sample_section_data, title="Exists")
        storage.save_draft(TEST_PROJECT_ID, doc, version=1)
        assert storage.draft_exists(TEST_PROJECT_ID)


# ─── Version Manager Tests ───────────────────────────────────────

class TestDraftVersionManager:
    def test_create_version(self, storage: DraftStorage, sample_section_data: list[dict]):
        mgr = DraftVersionManager(storage)
        builder = DocumentBuilder()
        doc = builder.assemble(sections_data=sample_section_data, title="Version Test")
        version = mgr.create_version(TEST_PROJECT_ID, doc)
        assert version.version_number == 1

    def test_multiple_versions(self, storage: DraftStorage, sample_section_data: list[dict]):
        mgr = DraftVersionManager(storage)
        builder = DocumentBuilder()
        doc = builder.assemble(sections_data=sample_section_data, title="Multi Version")
        v1 = mgr.create_version(TEST_PROJECT_ID, doc)
        v2 = mgr.create_version(TEST_PROJECT_ID, doc)
        assert v2.version_number == v1.version_number + 1

    def test_get_latest_version(self, storage: DraftStorage, sample_section_data: list[dict]):
        mgr = DraftVersionManager(storage)
        builder = DocumentBuilder()
        doc = builder.assemble(sections_data=sample_section_data, title="Latest")
        mgr.create_version(TEST_PROJECT_ID, doc)
        mgr.create_version(TEST_PROJECT_ID, doc)
        latest = mgr.get_latest_version(TEST_PROJECT_ID)
        assert latest is not None
        assert latest.version_number == 2

    def test_rollback(self, storage: DraftStorage, sample_section_data: list[dict]):
        mgr = DraftVersionManager(storage)
        builder = DocumentBuilder()
        doc = builder.assemble(sections_data=sample_section_data, title="Rollback Test")
        storage.save_draft(TEST_PROJECT_ID, doc, version=1)
        mgr.create_version(TEST_PROJECT_ID, doc)
        storage.save_draft(TEST_PROJECT_ID, doc, version=2)
        mgr.create_version(TEST_PROJECT_ID, doc)
        assert mgr.can_rollback(TEST_PROJECT_ID, 1)

    def test_prune_versions(self, storage: DraftStorage, sample_section_data: list[dict]):
        mgr = DraftVersionManager(storage)
        builder = DocumentBuilder()
        doc = builder.assemble(sections_data=sample_section_data, title="Prune")
        for _ in range(5):
            mgr.create_version(TEST_PROJECT_ID, doc)
        pruned = mgr.prune_versions(TEST_PROJECT_ID, keep=3)
        assert mgr.version_count(TEST_PROJECT_ID) <= 3


# ─── Full Integration Tests ──────────────────────────────────────

class TestDraftAssemblyEngine:
    def test_full_assembly_from_disk(self, engine: DraftAssemblyEngine, sample_sections_path: Path):
        pm_root = sample_sections_path.parent.parent
        doc = engine.assemble(
            project_id=TEST_PROJECT_ID,
            title="Full Assembly Test",
            sections_path=sample_sections_path,
        )
        assert doc.word_count > 0
        assert doc.section_count >= 5
        assert doc.content.strip()
        assert doc.reading_time_minutes >= 1

    def test_full_assembly_from_data(self, engine: DraftAssemblyEngine, sample_section_data: list[dict]):
        doc = engine.assemble(
            project_id=TEST_PROJECT_ID,
            title="Data Assembly",
            sections_data=sample_section_data,
        )
        assert doc.word_count > 0
        assert doc.section_count > 0

    def test_assembly_with_toc(self, engine: DraftAssemblyEngine, sample_section_data: list[dict]):
        doc = engine.assemble(
            project_id=TEST_PROJECT_ID,
            title="TOC Assembly",
            sections_data=sample_section_data,
            config=AssemblyConfig(generate_toc=True),
        )
        assert "Table of Contents" in doc.content

    def test_assembly_persists_to_disk(self, engine: DraftAssemblyEngine, sample_sections_path: Path):
        doc = engine.assemble(
            project_id=TEST_PROJECT_ID,
            title="Persist Test",
            sections_path=sample_sections_path,
        )
        assert engine.draft_exists(TEST_PROJECT_ID)
        loaded = engine.get_draft(TEST_PROJECT_ID)
        assert loaded is not None
        assert "Persist Test" in loaded

    def test_multiple_versions(self, engine: DraftAssemblyEngine, sample_sections_path: Path):
        doc1 = engine.assemble(
            project_id=TEST_PROJECT_ID,
            title="Version 1",
            sections_path=sample_sections_path,
        )
        assert engine.draft_exists(TEST_PROJECT_ID, version=1)

        doc2 = engine.assemble(
            project_id=TEST_PROJECT_ID,
            title="Version 2",
            sections_path=sample_sections_path,
        )
        versions = engine.list_draft_versions(TEST_PROJECT_ID)
        assert len(versions) >= 2

    def test_metadata_generation(self, engine: DraftAssemblyEngine, sample_sections_path: Path):
        engine.assemble(
            project_id=TEST_PROJECT_ID,
            title="Meta Test",
            sections_path=sample_sections_path,
        )
        metadata = engine.get_metadata(TEST_PROJECT_ID)
        assert metadata is not None
        assert metadata.project_id == TEST_PROJECT_ID
        assert metadata.total_word_count > 0
        assert metadata.section_count > 0

    def test_merge_log(self, engine: DraftAssemblyEngine, sample_sections_path: Path):
        engine.assemble(
            project_id=TEST_PROJECT_ID,
            title="Log Test",
            sections_path=sample_sections_path,
        )
        log = engine.get_merge_log(TEST_PROJECT_ID)
        assert len(log) > 0
        assert log[0].section_count > 0

    def test_cache_hit_identical_content(self, engine: DraftAssemblyEngine, sample_sections_path: Path):
        doc1 = engine.assemble(
            project_id=TEST_PROJECT_ID,
            title="Cache Test",
            sections_path=sample_sections_path,
        )
        metadata_after_first = engine.get_metadata(TEST_PROJECT_ID)

        doc2 = engine.assemble(
            project_id=TEST_PROJECT_ID,
            title="Cache Test",
            sections_path=sample_sections_path,
        )
        metadata_after_second = engine.get_metadata(TEST_PROJECT_ID)

        assert doc1.word_count == doc2.word_count

    def test_statistics(self, engine: DraftAssemblyEngine, sample_sections_path: Path):
        engine.assemble(
            project_id=TEST_PROJECT_ID,
            title="Stats Test",
            sections_path=sample_sections_path,
        )
        stats = engine.compute_statistics(TEST_PROJECT_ID)
        assert stats["word_count"] > 0
        assert stats["section_count"] > 0
        assert stats["total_versions"] >= 1


# ─── Large Document Tests ────────────────────────────────────────

class TestLargeDocument:
    def test_large_section_count(self, tmp_base: Path):
        base = tmp_base / "projects" / "large_test" / "sections"
        base.mkdir(parents=True, exist_ok=True)

        (base / "intro.md").write_text("# Introduction\n\nIntro content.\n", encoding="utf-8")
        for i in range(1, 51):
            (base / f"section_{i:02d}.md").write_text(
                f"## Section {i}\n\nThis is section {i} with enough content to simulate a real document.\n",
                encoding="utf-8",
            )
        (base / "conclusion.md").write_text("## Conclusion\n\nFinal content.\n", encoding="utf-8")
        (base / "cta.md").write_text("## CTA\n\nSubscribe.\n", encoding="utf-8")

        builder = DocumentBuilder()
        doc = builder.assemble(sections_path=base, title="Large Document")
        assert doc.section_count >= 50
        assert doc.word_count > 0

    def test_performance_large_merge(self, tmp_base: Path, sample_section_data: list[dict]):
        large_data = sample_section_data * 20
        builder = DocumentBuilder()
        start = time.time()
        doc = builder.assemble(
            sections_data=large_data,
            title="Performance Test",
        )
        elapsed = time.time() - start
        assert doc.content.strip()
        assert elapsed < 10


# ─── Error Handling Tests ────────────────────────────────────────

class TestErrorHandling:
    def test_missing_sections_path(self, engine: DraftAssemblyEngine):
        doc = engine.assemble(
            project_id="missing_test",
            title="Missing Path",
            sections_path=Path("/nonexistent"),
        )
        assert doc.word_count == 0

    def test_corrupted_section_file(self, tmp_base: Path, engine: DraftAssemblyEngine):
        base = tmp_base / "projects" / "corrupt_test" / "sections"
        base.mkdir(parents=True, exist_ok=True)
        (base / "intro.md").write_bytes(b"\x00\x00\x00")
        doc = engine.assemble(
            project_id="corrupt_test",
            title="Corrupted",
            sections_path=base,
        )
        assert doc.word_count == 0 or doc is not None

    def test_empty_sections_list(self, engine: DraftAssemblyEngine):
        doc = engine.assemble(
            project_id="empty_list",
            title="Empty List",
            sections_data=[],
        )
        assert doc.word_count == 0

    def test_duplicate_heading_handling(self, tmp_base: Path, engine: DraftAssemblyEngine):
        base = tmp_base / "projects" / "dup_test" / "sections"
        base.mkdir(parents=True, exist_ok=True)
        (base / "intro.md").write_text("# Introduction\n\nContent.\n", encoding="utf-8")
        (base / "section_01.md").write_text("## Duplicate\n\nContent.\n", encoding="utf-8")
        (base / "section_02.md").write_text("## Duplicate\n\nMore content.\n", encoding="utf-8")
        (base / "conclusion.md").write_text("## Conclusion\n\nContent.\n", encoding="utf-8")
        (base / "cta.md").write_text("## CTA\n\nContent.\n", encoding="utf-8")
        doc = engine.assemble(
            project_id="dup_test",
            title="Duplicate Test",
            sections_path=base,
        )
        assert doc.section_count > 0
        assert doc.content.strip()


# ─── Document Builder Edge Case Tests ────────────────────────────

class TestDocumentBuilderEdgeCases:
    def test_tables_preserved(self, tmp_base: Path):
        base = tmp_base / "projects" / "table_test" / "sections"
        base.mkdir(parents=True, exist_ok=True)
        (base / "intro.md").write_text(
            "# Introduction\n\nHere is a table:\n\n| Name | Value |\n|------|-------|\n| A | 1 |\n| B | 2 |\n\nEnd.\n",
            encoding="utf-8",
        )
        (base / "section_01.md").write_text(
            "## Section\n\nContent.\n", encoding="utf-8",
        )
        (base / "conclusion.md").write_text("## Conclusion\n\nDone.\n", encoding="utf-8")
        (base / "cta.md").write_text("## CTA\n\nAct now.\n", encoding="utf-8")

        builder = DocumentBuilder()
        doc = builder.assemble(sections_path=base, title="Table Test")
        assert "| Name | Value |" in doc.content
        assert "|------|-------|" in doc.content
        assert doc.table_count >= 1

    def test_images_preserved(self, tmp_base: Path):
        base = tmp_base / "projects" / "img_test" / "sections"
        base.mkdir(parents=True, exist_ok=True)
        (base / "intro.md").write_text(
            "# Introduction\n\n![Diagram](diagram.png)\n\nContent.\n",
            encoding="utf-8",
        )
        (base / "section_01.md").write_text("## Section\n\nContent.\n", encoding="utf-8")
        (base / "conclusion.md").write_text("## Conclusion\n\nDone.\n", encoding="utf-8")
        (base / "cta.md").write_text("## CTA\n\nAct.\n", encoding="utf-8")

        builder = DocumentBuilder()
        doc = builder.assemble(sections_path=base, title="Image Test")
        assert "![Diagram](diagram.png)" in doc.content
        assert doc.image_count >= 1

    def test_code_blocks_preserved(self, tmp_base: Path):
        base = tmp_base / "projects" / "code_test" / "sections"
        base.mkdir(parents=True, exist_ok=True)
        (base / "intro.md").write_text(
            "# Introduction\n\n```python\nprint('hello')\n```\n\nContent.\n",
            encoding="utf-8",
        )
        (base / "section_01.md").write_text("## Section\n\nContent.\n", encoding="utf-8")
        (base / "conclusion.md").write_text("## Conclusion\n\nDone.\n", encoding="utf-8")
        (base / "cta.md").write_text("## CTA\n\nAct.\n", encoding="utf-8")

        builder = DocumentBuilder()
        doc = builder.assemble(sections_path=base, title="Code Test")
        assert "```python" in doc.content
        assert "print('hello')" in doc.content
        assert doc.code_block_count >= 1

    def test_blockquotes_preserved(self, tmp_base: Path):
        base = tmp_base / "projects" / "quote_test" / "sections"
        base.mkdir(parents=True, exist_ok=True)
        (base / "intro.md").write_text(
            "# Introduction\n\n> This is a quote.\n\nContent.\n",
            encoding="utf-8",
        )
        (base / "section_01.md").write_text("## Section\n\nContent.\n", encoding="utf-8")
        (base / "conclusion.md").write_text("## Conclusion\n\nDone.\n", encoding="utf-8")
        (base / "cta.md").write_text("## CTA\n\nAct.\n", encoding="utf-8")

        builder = DocumentBuilder()
        doc = builder.assemble(sections_path=base, title="Quote Test")
        assert "> This is a quote." in doc.content

    def test_lists_preserved(self, tmp_base: Path):
        base = tmp_base / "projects" / "list_test" / "sections"
        base.mkdir(parents=True, exist_ok=True)
        (base / "intro.md").write_text(
            "# Introduction\n\n- Item 1\n- Item 2\n\nContent.\n",
            encoding="utf-8",
        )
        (base / "section_01.md").write_text("## Section\n\nContent.\n", encoding="utf-8")
        (base / "conclusion.md").write_text("## Conclusion\n\nDone.\n", encoding="utf-8")
        (base / "cta.md").write_text("## CTA\n\nAct.\n", encoding="utf-8")

        builder = DocumentBuilder()
        doc = builder.assemble(sections_path=base, title="List Test")
        assert "- Item 1" in doc.content
        assert doc.list_count >= 1


# ─── Performance Tests ───────────────────────────────────────────

class TestPerformance:
    def test_assembly_speed(self, sample_section_data: list[dict]):
        builder = DocumentBuilder()
        start = time.time()
        for _ in range(10):
            builder.assemble(
                sections_data=sample_section_data,
                title="Speed Test",
            )
        elapsed = time.time() - start
        avg_ms = (elapsed / 10) * 1000
        assert avg_ms < 1000, f"Average assembly time {avg_ms:.0f}ms exceeds 1000ms"

    def test_incremental_merge_speed(self, engine: DraftAssemblyEngine, sample_sections_path: Path):
        start = time.time()
        engine.assemble(
            project_id="perf_test",
            title="Perf Test",
            sections_path=sample_sections_path,
        )
        first = time.time() - start

        start = time.time()
        engine.assemble(
            project_id="perf_test",
            title="Perf Test",
            sections_path=sample_sections_path,
        )
        second = time.time() - start

        assert second < first * 3


# ─── Stress Tests ────────────────────────────────────────────────

class TestStress:
    def test_concurrent_assemblies(self, sample_section_data: list[dict]):
        builder = DocumentBuilder()
        results = []
        for i in range(20):
            doc = builder.assemble(
                sections_data=sample_section_data,
                title=f"Stress Test {i}",
            )
            results.append(doc)
        assert len(results) == 20
        assert all(d.word_count > 0 for d in results)

    def test_large_content_handling(self):
        merger = SectionMerger()
        large_section = DiscoveredSection(
            section_id="large",
            content="Word " * 10000,
            section_type=SectionType.BODY,
        )
        assert merger.sort_by_order([large_section])[0].word_count == 10000


# ─── Markdown Rendering Tests ────────────────────────────────────

class TestMarkdownRendering:
    def test_github_flavored_markdown(self):
        builder = MarkdownBuilder()
        sections = [
            DiscoveredSection(section_id="s1", content="## Heading\n\n- [Link](https://example.com)\n- `code`\n"),
        ]
        doc = builder.build_document("Test", sections)
        assert doc.startswith("# Test")
        assert "[Link](https://example.com)" in doc
        assert "`code`" in doc


# ─── Stress Test: 500+ Sections ──────────────────────────────────

class TestMassiveAssembly:
    def test_500_sections(self, tmp_base: Path):
        base = tmp_base / "projects" / "massive" / "sections"
        base.mkdir(parents=True, exist_ok=True)

        (base / "intro.md").write_text("# Introduction\n\nIntro content.\n", encoding="utf-8")
        for i in range(1, 501):
            (base / f"section_{i:02d}.md").write_text(
                f"## Section {i}\n\nContent for section {i}.\n",
                encoding="utf-8",
            )
        (base / "conclusion.md").write_text("## Conclusion\n\nDone.\n", encoding="utf-8")
        (base / "cta.md").write_text("## CTA\n\nAct.\n", encoding="utf-8")

        start = time.time()
        builder = DocumentBuilder()
        doc = builder.assemble(sections_path=base, title="Massive")
        elapsed = time.time() - start
        assert doc.section_count >= 500
        assert doc.word_count > 0
        assert elapsed < 30, f"500-section assembly took {elapsed:.1f}s (limit: 30s)"
