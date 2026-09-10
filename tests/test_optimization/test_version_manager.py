"""Tests for VersionManager."""

from __future__ import annotations
import tempfile
import os
from optimization.version_manager import VersionManager
from optimization.optimization_models import OptimizationType, OptimizationStatus


class TestVersionManager:
    def test_init(self):
        vm = VersionManager()
        assert vm is not None

    def test_create_version(self):
        vm = VersionManager()
        v = vm.create_version(
            section_index=0,
            section_heading="# Introduction",
            prompt="SEO optimization",
            content_before="Old content",
            content_after="New content",
            scores_before={"seo": 70.0},
            scores_after={"seo": 95.0},
            optimization_type=OptimizationType.SEO,
        )
        assert v.section_index == 0
        assert v.content_before == "Old content"
        assert v.content_after == "New content"
        assert v.status == OptimizationStatus.SUCCESS
        assert v.version_id.startswith("v")

    def test_get_latest_version(self):
        vm = VersionManager()
        vm.create_version(0, "H1", "p1", "old", "new1", {"s": 70}, {"s": 80}, OptimizationType.SEO)
        vm.create_version(0, "H1", "p2", "new1", "new2", {"s": 80}, {"s": 95}, OptimizationType.SEO)
        latest = vm.get_latest_version(0)
        assert latest is not None
        assert latest.content_after == "new2"

    def test_get_latest_version_none(self):
        vm = VersionManager()
        latest = vm.get_latest_version(99)
        assert latest is None

    def test_get_all_versions(self):
        vm = VersionManager()
        vm.create_version(0, "H1", "p1", "old", "new", {"s": 70}, {"s": 80}, OptimizationType.SEO)
        vm.create_version(0, "H1", "p2", "new", "new2", {"s": 80}, {"s": 90}, OptimizationType.GRAMMAR)
        versions = vm.get_all_versions(0)
        assert len(versions) == 2

    def test_get_version_to_rollback(self):
        vm = VersionManager()
        vm.create_version(0, "H1", "p1", "old", "new1", {"s": 70}, {"s": 80}, OptimizationType.SEO)
        vm.create_version(0, "H1", "p2", "new1", "new2", {"s": 80}, {"s": 75}, OptimizationType.SEO)
        rollback = vm.get_version_to_rollback(0)
        assert rollback is not None
        assert rollback.content_after == "new1"

    def test_get_version_to_rollback_single(self):
        vm = VersionManager()
        vm.create_version(0, "H1", "p1", "old", "new", {"s": 70}, {"s": 80}, OptimizationType.SEO)
        rollback = vm.get_version_to_rollback(0)
        assert rollback is None

    def test_mark_rolled_back(self):
        vm = VersionManager()
        v = vm.create_version(0, "H1", "p1", "old", "new", {"s": 70}, {"s": 80}, OptimizationType.SEO)
        vm.mark_rolled_back(v.version_id)
        assert v.status == OptimizationStatus.ROLLED_BACK

    def test_persist_and_load_versions(self):
        vm = VersionManager(output_dir=tempfile.gettempdir())
        vm.create_version(0, "H1", "p1", "old", "new", {"s": 70}, {"s": 80}, OptimizationType.SEO)
        path = vm.persist_versions(project_id="test_proj")
        assert os.path.exists(path)

        vm2 = VersionManager(output_dir=tempfile.gettempdir())
        loaded = vm2.load_versions(project_id="test_proj")
        assert len(loaded) > 0
        os.unlink(path)

    def test_clear(self):
        vm = VersionManager()
        vm.create_version(0, "H1", "p1", "old", "new", {"s": 70}, {"s": 80}, OptimizationType.SEO)
        vm.clear()
        assert vm._versions == {}
        assert vm._version_counter == 0
