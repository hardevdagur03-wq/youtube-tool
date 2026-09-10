from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest


@pytest.fixture
def sample_sections_path(tmp_path):
    base = tmp_path / "projects" / "test_draft" / "sections"
    base.mkdir(parents=True, exist_ok=True)
    (base / "intro.md").write_text("# Introduction\n\nThis is the introduction section.\n", encoding="utf-8")
    (base / "section_01.md").write_text("## First Section\n\nThis is the first body section.\n", encoding="utf-8")
    (base / "section_02.md").write_text("## Second Section\n\nThis is the second body section.\n", encoding="utf-8")
    (base / "faq.md").write_text("## FAQ\n\n### What is this?\n\nThis is a test.\n", encoding="utf-8")
    (base / "conclusion.md").write_text("## Conclusion\n\nThis is the conclusion.\n", encoding="utf-8")
    (base / "cta.md").write_text("## Next Steps\n\nSubscribe for more.\n", encoding="utf-8")
    return base


@pytest.fixture
def sample_section_data():
    return [
        {"section_id": "intro", "type": "introduction", "heading": "Introduction", "content": "# Introduction\n\nWelcome.\n", "order": 0},
        {"section_id": "section_01", "type": "body", "heading": "Getting Started", "content": "## Getting Started\n\nContent.\n", "order": 1},
        {"section_id": "section_02", "type": "body", "heading": "Advanced", "content": "## Advanced\n\nDeeper dive.\n", "order": 2},
        {"section_id": "faq", "type": "faq", "heading": "FAQ", "content": "## FAQ\n\n### Q?\n\nA.\n", "order": 3},
        {"section_id": "conclusion", "type": "conclusion", "heading": "Conclusion", "content": "## Conclusion\n\nFinal.\n", "order": 4},
        {"section_id": "cta", "type": "cta", "heading": "Next Steps", "content": "## Next Steps\n\nAct now.\n", "order": 5},
    ]


class TestSectionDiscovery:
    def test_discover_from_disk(self, sample_sections_path):
        from draft.section_merger import SectionMerger
        merger = SectionMerger()
        sections = merger.discover_sections(sample_sections_path)
        assert len(sections) >= 5

    def test_discover_from_list(self, sample_section_data):
        from draft.section_merger import SectionMerger
        merger = SectionMerger()
        sections = merger.discover_from_list(sample_section_data)
        assert len(sections) == 6

    def test_discover_empty_directory(self, tmp_path):
        from draft.section_merger import SectionMerger
        merger = SectionMerger()
        sections = merger.discover_sections(tmp_path / "empty")
        assert len(sections) == 0

    def test_section_ordering(self, sample_sections_path):
        from draft.section_merger import SectionMerger
        from draft.draft_models import SectionType
        merger = SectionMerger()
        sections = merger.discover_sections(sample_sections_path)
        sorted_s = merger.sort_by_order(sections)
        types = [s.section_type for s in sorted_s]
        assert types.index(SectionType.INTRODUCTION) < types.index(SectionType.FAQ)

    def test_check_completeness(self):
        from draft.section_merger import SectionMerger
        from draft.draft_models import DiscoveredSection, SectionType
        merger = SectionMerger()
        sections = [
            DiscoveredSection(section_id="i", section_type=SectionType.INTRODUCTION),
            DiscoveredSection(section_id="b", section_type=SectionType.BODY),
            DiscoveredSection(section_id="c", section_type=SectionType.CONCLUSION),
            DiscoveredSection(section_id="cta", section_type=SectionType.CTA),
        ]
        complete, missing = merger.check_completeness(sections)
        assert complete
        assert len(missing) == 0


class TestDocumentValidator:
    def test_validate_valid_section(self):
        from draft.document_validator import DocumentValidator
        from draft.draft_models import DiscoveredSection
        validator = DocumentValidator()
        section = DiscoveredSection(section_id="intro", content="# Valid Heading\n\nThis is valid content with enough words.\n")
        result = validator.validate_section(section)
        assert result.exists
        assert result.valid

    def test_validate_empty_section(self):
        from draft.document_validator import DocumentValidator
        from draft.draft_models import DiscoveredSection
        validator = DocumentValidator()
        section = DiscoveredSection(section_id="empty", content="")
        result = validator.validate_section(section)
        assert not result.exists

    def test_heading_counting(self):
        from draft.document_validator import DocumentValidator
        validator = DocumentValidator()
        assert validator.count_headings("# H1\n\n## H2\n\n### H3\n") == 3

    def test_table_counting(self):
        from draft.document_validator import DocumentValidator
        validator = DocumentValidator()
        assert validator.count_tables("| H1 | H2 |\n|----|----|\n| A | B |\n") == 1


class TestHeadingNormalizer:
    def test_normalize_intro_to_h2(self):
        from draft.heading_normalizer import HeadingNormalizer
        from draft.draft_models import DiscoveredSection, SectionType
        normalizer = HeadingNormalizer()
        intro = DiscoveredSection(section_id="intro", content="# Introduction\n\nContent.\n", section_type=SectionType.INTRODUCTION)
        normalized = normalizer.normalize([intro])
        assert "## Introduction" in normalized[0].content

    def test_anchor_id_generation(self):
        from draft.heading_normalizer import HeadingNormalizer
        normalizer = HeadingNormalizer()
        assert normalizer.get_anchor_id("Hello World") == "hello-world"


class TestMarkdownBuilder:
    def test_build_document(self):
        from draft.markdown_builder import MarkdownBuilder
        from draft.draft_models import DiscoveredSection
        builder = MarkdownBuilder()
        sections = [DiscoveredSection(section_id="intro", content="## Intro\n\nContent\n")]
        doc = builder.build_document("Test Title", sections)
        assert doc.startswith("# Test Title")
        assert "## Intro" in doc

    def test_format_table(self):
        from draft.markdown_builder import MarkdownBuilder
        builder = MarkdownBuilder()
        table = builder.format_table(headers=["Name", "Age"], rows=[["Alice", "30"]])
        assert "| Name" in table

    def test_format_code_block(self):
        from draft.markdown_builder import MarkdownBuilder
        builder = MarkdownBuilder()
        code = builder.format_code_block("print('hello')", language="python")
        assert "```python" in code


class TestDocumentBuilder:
    def test_assemble_from_disk(self, sample_sections_path):
        from draft.document_builder import DocumentBuilder
        builder = DocumentBuilder()
        doc = builder.assemble(sections_path=sample_sections_path, title="Test Blog Post")
        assert doc.word_count > 0
        assert doc.section_count >= 5

    def test_assemble_from_data(self, sample_section_data):
        from draft.document_builder import DocumentBuilder
        builder = DocumentBuilder()
        doc = builder.assemble(sections_data=sample_section_data, title="Data Test")
        assert doc.word_count > 0
        assert doc.section_count == 6

    def test_assemble_empty(self):
        from draft.document_builder import DocumentBuilder
        builder = DocumentBuilder()
        doc = builder.assemble(title="Empty")
        assert doc.word_count == 0

    def test_assemble_with_toc(self, sample_section_data):
        from draft.document_builder import DocumentBuilder
        from draft.draft_models import AssemblyConfig
        builder = DocumentBuilder()
        doc = builder.assemble(sections_data=sample_section_data, title="TOC Test", config=AssemblyConfig(generate_toc=True))
        assert "Table of Contents" in doc.content


class TestDraftStorage:
    def test_save_and_load_draft(self, tmp_path):
        from draft.draft_storage import DraftStorage
        from draft.document_builder import DocumentBuilder
        storage = DraftStorage(base_path=str(tmp_path))
        builder = DocumentBuilder()
        doc = builder.assemble(sections_data=[{"section_id": "intro", "type": "introduction", "heading": "Intro", "content": "# Intro\n\nContent\n", "order": 0}], title="Storage Test")
        storage.save_draft("test_proj", doc, version=1)
        loaded = storage.load_draft("test_proj", version=1)
        assert loaded is not None

    def test_draft_versioning(self, tmp_path):
        from draft.draft_storage import DraftStorage
        from draft.draft_models import DraftVersion
        storage = DraftStorage(base_path=str(tmp_path))
        v1 = DraftVersion(version_number=1)
        v2 = DraftVersion(version_number=2)
        storage.save_version("test_proj", v1)
        storage.save_version("test_proj", v2)
        versions = storage.list_versions("test_proj")
        assert len(versions) == 2


class TestDraftVersionManager:
    def test_create_version(self, tmp_path):
        from draft.version_manager import DraftVersionManager
        from draft.draft_storage import DraftStorage
        from draft.document_builder import DocumentBuilder
        storage = DraftStorage(base_path=str(tmp_path))
        mgr = DraftVersionManager(storage)
        builder = DocumentBuilder()
        doc = builder.assemble(sections_data=[{"section_id": "intro", "type": "introduction", "content": "Hi", "order": 0}], title="V")
        version = mgr.create_version("test_proj", doc)
        assert version.version_number == 1

    def test_multiple_versions(self, tmp_path):
        from draft.version_manager import DraftVersionManager
        from draft.draft_storage import DraftStorage
        from draft.document_builder import DocumentBuilder
        storage = DraftStorage(base_path=str(tmp_path))
        mgr = DraftVersionManager(storage)
        builder = DocumentBuilder()
        doc = builder.assemble(title="MV")
        v1 = mgr.create_version("test_proj", doc)
        v2 = mgr.create_version("test_proj", doc)
        assert v2.version_number == v1.version_number + 1


class TestDraftAssemblyEngine:
    def test_full_assembly_from_disk(self, sample_sections_path):
        from draft.draft_assembly_engine import DraftAssemblyEngine
        from draft.draft_storage import DraftStorage
        storage = DraftStorage(base_path=str(sample_sections_path.parent.parent.parent))
        engine = DraftAssemblyEngine(storage=storage)
        doc = engine.assemble(project_id="test_draft", title="Full Assembly Test", sections_path=sample_sections_path)
        assert doc.word_count > 0
        assert doc.section_count >= 5

    def test_assembly_with_toc(self, sample_section_data):
        from draft.draft_assembly_engine import DraftAssemblyEngine
        from draft.draft_storage import DraftStorage
        from draft.draft_models import AssemblyConfig
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = DraftStorage(base_path=tmpdir)
            engine = DraftAssemblyEngine(storage=storage)
            doc = engine.assemble(project_id="toc", title="TOC", sections_data=sample_section_data, config=AssemblyConfig(generate_toc=True))
            assert "Table of Contents" in doc.content

    def test_statistics(self, sample_sections_path):
        from draft.draft_assembly_engine import DraftAssemblyEngine
        from draft.draft_storage import DraftStorage
        storage = DraftStorage(base_path=str(sample_sections_path.parent.parent.parent))
        engine = DraftAssemblyEngine(storage=storage)
        engine.assemble(project_id="stats", title="Stats", sections_path=sample_sections_path)
        stats = engine.compute_statistics("stats")
        assert stats["word_count"] > 0
        assert stats["section_count"] > 0
