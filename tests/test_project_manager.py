"""Tests for the Project Management Layer.

All existing tests continue to work unchanged.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from projects.project_models import (
    ArtifactInfo,
    Checkpoint,
    HistoryEntry,
    PipelineStage,
    PipelineStatus,
    Project,
    ProjectSettings,
    ProjectStatistics,
    ProjectStatus,
    StageInfo,
    StageStatus,
    Version,
    utc_now,
)
from projects.uuid_manager import UUIDManager
from projects.storage_manager import StorageManager
from projects.progress_tracker import ProgressTracker
from projects.checkpoint_manager import CheckpointManager
from projects.version_manager import VersionManager
from projects.history_manager import HistoryManager
from projects.recovery_engine import RecoveryEngine
from projects.project_manager import ProjectManager
from projects.project_service import ProjectService


# ---------------------------------------------------------------------------
# Project Models
# ---------------------------------------------------------------------------


class TestProjectModels:
    def test_project_defaults(self):
        p = Project(project_id="test123")
        assert p.project_id == "test123"
        assert p.status == ProjectStatus.CREATED
        assert p.version == 1
        assert len(p.pipeline.stages) == 0

    def test_project_status_enum(self):
        assert ProjectStatus.CREATED.value == "created"
        assert ProjectStatus.COMPLETED.value == "completed"
        assert ProjectStatus.FAILED.value == "failed"
        assert ProjectStatus.CANCELLED.value == "cancelled"
        assert ProjectStatus.PAUSED.value == "paused"
        assert ProjectStatus.RESUMED.value == "resumed"

    def test_pipeline_stages_enum(self):
        stages = list(PipelineStage)
        assert len(stages) == 12
        assert stages[0] == PipelineStage.METADATA
        assert stages[-1] == PipelineStage.EXPORT

    def test_stage_info_defaults(self):
        si = StageInfo(stage=PipelineStage.METADATA)
        assert si.status == StageStatus.PENDING
        assert si.progress_pct == 0.0
        assert si.retry_count == 0

    def test_pipeline_status_defaults(self):
        ps = PipelineStatus()
        assert ps.stages == {}
        assert ps.overall_progress_pct == 0.0
        assert ps.is_paused is False

    def test_project_settings_defaults(self):
        s = ProjectSettings()
        assert s.language == "en"
        assert s.seo_enabled is True
        assert "markdown" in s.export_formats

    def test_artifact_info(self):
        a = ArtifactInfo(path="/tmp/test.csv", file_type="csv", file_size_bytes=100, created_at=utc_now(), stage="metadata")
        assert a.file_type == "csv"
        assert a.stage == "metadata"

    def test_checkpoint_model(self):
        cp = Checkpoint(checkpoint_id="cp_test", stage="metadata", created_at=utc_now(), reason="test")
        assert cp.checkpoint_id == "cp_test"
        assert cp.reason == "test"

    def test_version_model(self):
        v = Version(version_id="v_test", version_number=1, created_at=utc_now(), reason="initial")
        assert v.version_number == 1
        assert v.parent_version == ""

    def test_history_entry(self):
        e = HistoryEntry(entry_id="ev_test", timestamp=utc_now(), action="created", stage="metadata")
        assert e.action == "created"
        assert e.system_action is True

    def test_project_statistics_defaults(self):
        s = ProjectStatistics()
        assert s.word_count == 0
        assert s.total_api_calls == 0
        assert s.cache_hits == 0


# ---------------------------------------------------------------------------
# UUID Manager
# ---------------------------------------------------------------------------


class TestUUIDManager:
    def test_generate_uuid(self):
        uid = UUIDManager.generate_uuid()
        assert len(uid) == 32
        assert UUIDManager.validate_uuid(uid)

    def test_short_id(self):
        sid = UUIDManager.generate_short_id()
        assert len(sid) == 8

    def test_project_id(self):
        pid = UUIDManager.generate_project_id()
        assert len(pid) == 32

    def test_checkpoint_id(self):
        cpid = UUIDManager.generate_checkpoint_id()
        assert cpid.startswith("cp_")

    def test_version_id(self):
        vid = UUIDManager.generate_version_id()
        assert vid.startswith("v_")

    def test_history_id(self):
        hid = UUIDManager.generate_history_id()
        assert hid.startswith("ev_")

    def test_safe_folder_name(self):
        assert UUIDManager.safe_folder_name("Hello World!") == "hello_world"
        assert UUIDManager.safe_folder_name("test@#$%^") == "test"
        assert UUIDManager.safe_folder_name("") == "project"
        assert len(UUIDManager.safe_folder_name("a" * 100)) <= 64

    def test_validate_uuid(self):
        uid = UUIDManager.generate_uuid()
        assert UUIDManager.validate_uuid(uid) is True
        assert UUIDManager.validate_uuid("") is False
        assert UUIDManager.validate_uuid("not-a-uuid") is False

    def test_checksum(self):
        cs1 = UUIDManager.checksum("hello")
        cs2 = UUIDManager.checksum("hello")
        assert cs1 == cs2
        assert len(cs1) == 16


# ---------------------------------------------------------------------------
# Storage Manager
# ---------------------------------------------------------------------------


class TestStorageManager:
    def test_create_and_load(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        sm.create_project_dir("proj123")
        sm.save_json("proj123", "test.json", {"key": "value"})
        data = sm.load_json("proj123", "test.json")
        assert data == {"key": "value"}

    def test_file_exists(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        sm.create_project_dir("proj123")
        sm.save_json("proj123", "test.json", {})
        assert sm.file_exists("proj123", "test.json") is True
        assert sm.file_exists("proj123", "missing.json") is False

    def test_load_nonexistent(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        assert sm.load_json("nonexistent", "test.json") is None

    def test_delete_project(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        sm.create_project_dir("proj123")
        sm.save_json("proj123", "project.json", {"id": "123"})
        assert sm.project_exists("proj123")
        assert sm.delete_project("proj123", permanent=True)
        assert not sm.project_exists("proj123")

    def test_list_projects(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        sm.create_project_dir("p1")
        sm.save_json("p1", "project.json", {})
        sm.create_project_dir("p2")
        sm.save_json("p2", "project.json", {})
        projects = sm.list_projects()
        assert len(projects) == 2
        assert "p1" in projects
        assert "p2" in projects

    def test_storage_usage(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        sm.create_project_dir("proj123")
        sm.save_json("proj123", "test.json", {"data": "x" * 1000})
        usage = sm.get_storage_usage("proj123")
        assert usage > 0

    def test_atomic_write(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        sm.create_project_dir("proj123")
        sm.save_json("proj123", "data.json", {"value": 42})
        path = sm.project_file("proj123", "data.json")
        assert path.exists()
        # No .tmp file should remain
        assert not path.with_suffix(".tmp").exists()


# ---------------------------------------------------------------------------
# Progress Tracker
# ---------------------------------------------------------------------------


class TestProgressTracker:
    def test_compute_overall_progress_empty(self):
        assert ProgressTracker.compute_overall_progress({}) == 0.0

    def test_compute_overall_progress_complete(self):
        stages = {}
        for s in PipelineStage:
            stages[s.value] = StageInfo(stage=s, status=StageStatus.COMPLETED)
        assert ProgressTracker.compute_overall_progress(stages) == 100.0

    def test_compute_overall_progress_partial(self):
        stages = {}
        for i, s in enumerate(PipelineStage):
            status = StageStatus.COMPLETED if i < 3 else StageStatus.PENDING
            stages[s.value] = StageInfo(stage=s, status=status)
        pct = ProgressTracker.compute_overall_progress(stages)
        assert 0 < pct < 100

    def test_next_stage(self):
        stages = {}
        for s in PipelineStage:
            stages[s.value] = StageInfo(stage=s, status=StageStatus.PENDING)
        assert ProgressTracker.next_stage(stages) == "metadata"
        stages["metadata"].status = StageStatus.COMPLETED
        assert ProgressTracker.next_stage(stages) == "transcript"

    def test_incomplete_stages(self):
        stages = {}
        stages["metadata"] = StageInfo(stage=PipelineStage.METADATA, status=StageStatus.COMPLETED)
        incomplete = ProgressTracker.incomplete_stages(stages)
        assert "metadata" not in incomplete
        assert "transcript" in incomplete

    def test_format_duration(self):
        assert ProgressTracker.format_duration(0.5) == "<1s"
        assert ProgressTracker.format_duration(30) == "30s"
        assert ProgressTracker.format_duration(90) == "1m 30s"
        assert ProgressTracker.format_duration(3661) == "1h 1m"

    def test_compute_speed(self):
        assert ProgressTracker.compute_speed(100, 10) == "10.0 items/s"
        assert ProgressTracker.compute_speed(1, 10) == "10.0s/item"

    def test_stage_summary(self):
        stages = {}
        stages["metadata"] = StageInfo(stage=PipelineStage.METADATA, status=StageStatus.COMPLETED)
        stages["transcript"] = StageInfo(stage=PipelineStage.TRANSCRIPT, status=StageStatus.RUNNING)
        summary = ProgressTracker.stage_summary(stages)
        assert summary["completed"] == 1
        assert summary["running"] == 1
        assert summary["total"] == 12


# ---------------------------------------------------------------------------
# Checkpoint Manager
# ---------------------------------------------------------------------------


class TestCheckpointManager:
    def test_create_checkpoint(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        cm = CheckpointManager(sm)
        sm.create_project_dir("proj123")
        sm.save_json("proj123", "project.json", {"status": "running"})
        cp = cm.create_checkpoint("proj123", PipelineStage.METADATA, "test")
        assert cp.stage == "metadata"
        assert cp.checkpoint_id.startswith("cp_")

    def test_get_latest_checkpoint(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        cm = CheckpointManager(sm)
        sm.create_project_dir("proj123")
        sm.save_json("proj123", "project.json", {"v": 1})
        cm.create_checkpoint("proj123", PipelineStage.METADATA, "first")
        cm.create_checkpoint("proj123", PipelineStage.TRANSCRIPT, "second")
        latest = cm.get_latest_checkpoint("proj123")
        assert latest is not None
        assert latest.reason == "second"

    def test_validate_checkpoint(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        cm = CheckpointManager(sm)
        sm.create_project_dir("proj123")
        sm.save_json("proj123", "project.json", {"status": "ok"})
        cp = cm.create_checkpoint("proj123", PipelineStage.METADATA)
        assert cm.validate_checkpoint("proj123", cp) is True

    def test_validate_checkpoint_missing_file(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        cm = CheckpointManager(sm)
        sm.create_project_dir("proj123")
        cp = Checkpoint(
            checkpoint_id="cp_test", stage="metadata",
            created_at=utc_now(), reason="test",
            files={"nonexistent": "nope.json"},
        )
        assert cm.validate_checkpoint("proj123", cp) is False


# ---------------------------------------------------------------------------
# Version Manager
# ---------------------------------------------------------------------------


class TestVersionManager:
    def test_create_version(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        vm = VersionManager(sm)
        sm.create_project_dir("proj123")
        v = vm.create_version("proj123", {"key": "value"}, "initial")
        assert v.version_number == 1
        assert v.reason == "initial"

    def test_get_versions(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        vm = VersionManager(sm)
        sm.create_project_dir("proj123")
        vm.create_version("proj123", {"v": 1}, "first")
        vm.create_version("proj123", {"v": 2}, "second")
        versions = vm.get_versions("proj123")
        assert len(versions) == 2
        assert versions[1].version_number == 2

    def test_get_latest_version(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        vm = VersionManager(sm)
        sm.create_project_dir("proj123")
        vm.create_version("proj123", {"v": 1}, "first")
        vm.create_version("proj123", {"v": 2}, "second")
        latest = vm.get_latest_version("proj123")
        assert latest.version_number == 2


# ---------------------------------------------------------------------------
# History Manager
# ---------------------------------------------------------------------------


class TestHistoryManager:
    def test_record_entry(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        hm = HistoryManager(sm)
        sm.create_project_dir("proj123")
        entry = hm.record("proj123", "test_action", stage="metadata")
        assert entry.action == "test_action"
        assert entry.stage == "metadata"
        assert entry.entry_id.startswith("ev_")

    def test_get_history(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        hm = HistoryManager(sm)
        sm.create_project_dir("proj123")
        hm.record("proj123", "action1")
        hm.record("proj123", "action2")
        history = hm.get_history("proj123")
        assert len(history) == 2

    def test_get_history_for_stage(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        hm = HistoryManager(sm)
        sm.create_project_dir("proj123")
        hm.record("proj123", "a1", stage="metadata")
        hm.record("proj123", "a2", stage="transcript")
        hm.record("proj123", "a3", stage="metadata")
        meta_entries = hm.get_history_for_stage("proj123", "metadata")
        assert len(meta_entries) == 2

    def test_clear_history(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        hm = HistoryManager(sm)
        sm.create_project_dir("proj123")
        hm.record("proj123", "a1")
        hm.record("proj123", "a2")
        hm.clear_history("proj123")
        assert len(hm.get_history("proj123")) == 0


# ---------------------------------------------------------------------------
# Recovery Engine
# ---------------------------------------------------------------------------


class TestRecoveryEngine:
    def test_needs_recovery_no_project(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        cm = CheckpointManager(sm)
        re = RecoveryEngine(sm, cm)
        needs, reason = re.needs_recovery("nonexistent")
        assert not needs
        assert reason == "no_project"

    def test_needs_recovery_complete(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        cm = CheckpointManager(sm)
        re = RecoveryEngine(sm, cm)
        sm.create_project_dir("proj123")
        sm.save_json("proj123", "project.json", {"status": "completed"})
        needs, reason = re.needs_recovery("proj123")
        assert not needs

    def test_validate_artifacts_missing(self, tmp_path):
        sm = StorageManager(root=tmp_path)
        cm = CheckpointManager(sm)
        re = RecoveryEngine(sm, cm)
        sm.create_project_dir("proj123")
        sm.save_json("proj123", "project.json", {
            "pipeline": {
                "stages": {
                    "metadata": {"status": "completed"},
                },
            },
        })
        issues = re.validate_artifacts("proj123")
        assert any("metadata.json missing" in i["message"] for i in issues)


# ---------------------------------------------------------------------------
# Project Manager (Integration)
# ---------------------------------------------------------------------------


class TestProjectManager:
    def test_create_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        pm = ProjectManager()
        project = pm.create_project(url="https://youtube.com/watch?v=test123", video_id="test123")
        assert project.project_id is not None
        assert project.video_id == "test123"
        assert project.status == ProjectStatus.CREATED
        assert len(project.pipeline.stages) == 12

    def test_get_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        pm = ProjectManager()
        created = pm.create_project(url="https://youtube.com/watch?v=test123", video_id="test123")
        loaded = pm.get_project(created.project_id)
        assert loaded is not None
        assert loaded.project_id == created.project_id

    def test_get_nonexistent_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        pm = ProjectManager()
        assert pm.get_project("nonexistent") is None

    def test_delete_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        pm = ProjectManager()
        created = pm.create_project(url="https://youtube.com/watch?v=test123")
        assert pm.delete_project(created.project_id, permanent=True) is True
        assert pm.get_project(created.project_id) is None

    def test_list_projects(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        pm = ProjectManager()
        p1 = pm.create_project(video_id="v1")
        p2 = pm.create_project(video_id="v2")
        p3 = pm.create_project(video_id="v3")
        pm.storage.delete_project(p1.project_id, permanent=True)
        pm.storage.delete_project(p2.project_id, permanent=True)
        pm.storage.delete_project(p3.project_id, permanent=True)
        # Verify they no longer appear
        projects = pm.list_projects()
        pids = [p.project_id for p in projects]
        assert p1.project_id not in pids
        assert p2.project_id not in pids
        assert p3.project_id not in pids

    def test_search_projects(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        pm = ProjectManager()
        p1 = pm.create_project(video_id="abc123", name="Python Tutorial")
        p2 = pm.create_project(video_id="xyz789", name="JavaScript Guide")
        results = pm.search_projects("python")
        matched_ids = [r.project_id for r in results]
        assert p1.project_id in matched_ids
        assert p2.project_id not in matched_ids

    def test_stage_lifecycle(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        pm = ProjectManager()
        project = pm.create_project(video_id="test123")
        pid = project.project_id

        pm.stage_started(pid, PipelineStage.METADATA)
        p = pm.get_project(pid)
        assert p.pipeline.current_stage == "metadata"
        assert p.pipeline.stages["metadata"].status == StageStatus.RUNNING

        pm.stage_completed(pid, PipelineStage.METADATA)
        p = pm.get_project(pid)
        assert p.pipeline.stages["metadata"].status == StageStatus.COMPLETED

        pm.stage_failed(pid, PipelineStage.TRANSCRIPT, "API error")
        p = pm.get_project(pid)
        assert p.status == ProjectStatus.FAILED
        assert p.error == "API error"

    def test_complete_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        pm = ProjectManager()
        project = pm.create_project(video_id="test123")
        for s in PipelineStage:
            pm.stage_started(project.project_id, s)
            pm.stage_completed(project.project_id, s)
        pm.complete_project(project.project_id)
        p = pm.get_project(project.project_id)
        assert p.status == ProjectStatus.COMPLETED
        assert p.pipeline.overall_progress_pct == 100.0

    def test_pause_resume_cancel(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        pm = ProjectManager()
        project = pm.create_project(video_id="test123")
        pid = project.project_id

        paused = pm.pause_project(pid)
        assert paused
        p = pm.get_project(pid)
        assert p.status == ProjectStatus.PAUSED

        recovered = pm.resume_project(pid)
        assert recovered is not None
        p = pm.get_project(pid)
        assert p.status == ProjectStatus.RESUMED

        cancelled = pm.cancel_project(pid)
        assert cancelled
        p = pm.get_project(pid)
        assert p.status == ProjectStatus.CANCELLED

    def test_find_or_create_by_video(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        pm = ProjectManager()
        p1 = pm.find_or_create_by_video("test123", "https://youtube.com/watch?v=test123")
        p2 = pm.find_or_create_by_video("test123")
        assert p1.project_id == p2.project_id

    def test_get_summary(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        pm = ProjectManager()
        project = pm.create_project(video_id="test123", name="Test Summary")
        summary = pm.get_summary(project.project_id)
        assert summary is not None
        assert summary["name"] == "Test Summary"
        assert summary["video_id"] == "test123"
        assert "overall_progress_pct" in summary


# ---------------------------------------------------------------------------
# Project Service
# ---------------------------------------------------------------------------


class TestProjectService:
    def test_create_from_url(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        ps = ProjectService()
        result = ps.create_from_url("https://youtube.com/watch?v=test123", "test123")
        assert result["video_id"] == "test123"
        assert result["status"] == "created"
        assert "project_id" in result

    def test_get_list_delete(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        ps = ProjectService()
        result = ps.create_from_url("https://youtube.com/watch?v=v1", "v1")
        pid = result["project_id"]

        fetched = ps.get(pid)
        assert fetched is not None

        projects = ps.list_all()
        assert len(projects) >= 1

        ps.delete(pid, permanent=True)
        assert ps.get(pid) is None

    def test_pause_resume_cancel_service(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        ps = ProjectService()
        result = ps.create_from_url("https://youtube.com/watch?v=v1", "v1")
        pid = result["project_id"]

        assert ps.pause(pid)["success"]
        resumed = ps.resume(pid)
        assert resumed is not None
        assert resumed["status"] == "resumed"
        assert ps.cancel(pid)["success"]

    def test_stage_progress_tracking(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        ps = ProjectService()
        result = ps.create_from_url("https://youtube.com/watch?v=v1", "v1")
        pid = result["project_id"]

        ps.manager.stage_started(pid, PipelineStage.METADATA)
        ps.manager.update_stage_progress(pid, PipelineStage.METADATA, 50.0)
        ps.manager.stage_completed(pid, PipelineStage.METADATA)

        project = ps.get(pid)
        assert project["pipeline"]["stages"]["metadata"]["status"] == "completed"
        assert project["pipeline"]["stages"]["metadata"]["progress_pct"] == 100.0

    def test_history_tracking(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        ps = ProjectService()
        result = ps.create_from_url("https://youtube.com/watch?v=v1", "v1")
        pid = result["project_id"]

        ps.manager.stage_started(pid, PipelineStage.METADATA)
        ps.manager.stage_completed(pid, PipelineStage.METADATA)

        history = ps.get_history(pid)
        assert len(history) >= 2  # created + started + completed

    def test_settings_update(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        ps = ProjectService()
        result = ps.create_from_url("https://youtube.com/watch?v=v1", "v1")
        pid = result["project_id"]

        updated = ps.update_settings(pid, {"language": "hi", "seo_enabled": False})
        assert updated["settings"]["language"] == "hi"
        assert updated["settings"]["seo_enabled"] is False

    def test_validate_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        ps = ProjectService()
        result = ps.create_from_url("https://youtube.com/watch?v=v1", "v1")
        pid = result["project_id"]

        validation = ps.validate(pid)
        assert isinstance(validation, list)

    def test_get_stats(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        ps = ProjectService()
        ps.create_from_url("https://youtube.com/watch?v=v1", "v1")
        ps.create_from_url("https://youtube.com/watch?v=v2", "v2")
        stats = ps.get_stats()
        assert stats["total_projects"] >= 2
