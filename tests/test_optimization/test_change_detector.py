"""Tests for ChangeDetector."""

from __future__ import annotations
from optimization.change_detector import ChangeDetector
from optimization.optimization_models import OptimizedSection, OptimizationStatus


class TestChangeDetector:
    def test_init(self):
        cd = ChangeDetector()
        assert cd is not None

    def test_detect_changes_unchanged(self):
        cd = ChangeDetector()
        result = cd.detect_changes("Same content", "Same content")
        assert result["changed"] is False
        assert result["diff_ratio"] == 1.0

    def test_detect_changes_modified(self):
        cd = ChangeDetector()
        result = cd.detect_changes("Original content here", "Modified content here")
        assert result["changed"] is True
        assert result["diff_ratio"] < 1.0
        assert len(result["modifications"]) > 0

    def test_was_section_optimized(self):
        cd = ChangeDetector()
        section = OptimizedSection(
            section_index=0,
            heading="Test",
            original_content="Old",
            optimized_content="New",
            status=OptimizationStatus.SUCCESS,
        )
        assert cd.was_section_optimized(section) is True

    def test_was_section_not_optimized(self):
        cd = ChangeDetector()
        section = OptimizedSection(
            section_index=0,
            heading="Test",
            original_content="Same",
            optimized_content="",
            status=OptimizationStatus.SKIPPED,
        )
        assert cd.was_section_optimized(section) is False

    def test_has_meaningful_change(self):
        cd = ChangeDetector()
        assert cd.has_meaningful_change("Hello world", "Hello world, how are you?") is True
        assert cd.has_meaningful_change("Same", "Same") is False

    def test_get_affected_headings(self):
        cd = ChangeDetector()
        orig = "# Intro\n\nContent.\n\n## Body\n\nMore."
        modified = "# Intro\n\nContent.\n\n## Body Changed\n\nMore.\n\n### Subsection\n\nNew."
        affected = cd.get_affected_headings(orig, modified)
        assert len(affected) > 0
