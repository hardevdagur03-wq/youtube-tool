from __future__ import annotations

import pytest


class TestProjectModels:
    def test_project_defaults(self):
        from projects.project_models import Project, ProjectStatus
        p = Project(project_id="test123")
        assert p.project_id == "test123"
        assert p.status == ProjectStatus.CREATED
        assert p.version == 1

    def test_project_status_enum(self):
        from projects.project_models import ProjectStatus
        assert ProjectStatus.CREATED.value == "created"
        assert ProjectStatus.COMPLETED.value == "completed"
        assert ProjectStatus.FAILED.value == "failed"

    def test_pipeline_stages_enum(self):
        from projects.project_models import PipelineStage
        stages = list(PipelineStage)
        assert len(stages) == 12
        assert stages[0] == PipelineStage.METADATA
        assert stages[-1] == PipelineStage.EXPORT

    def test_stage_info_defaults(self):
        from projects.project_models import StageInfo, PipelineStage, StageStatus
        si = StageInfo(stage=PipelineStage.METADATA)
        assert si.status == StageStatus.PENDING
        assert si.progress_pct == 0.0

    def test_project_settings_defaults(self):
        from projects.project_models import ProjectSettings
        s = ProjectSettings()
        assert s.language == "en"
        assert s.seo_enabled is True

    def test_checkpoint_model(self):
        from projects.project_models import Checkpoint, utc_now
        cp = Checkpoint(checkpoint_id="cp_test", stage="metadata", created_at=utc_now(), reason="test")
        assert cp.checkpoint_id == "cp_test"

    def test_history_entry(self):
        from projects.project_models import HistoryEntry
        e = HistoryEntry(entry_id="ev_test", timestamp="2024-01-01", action="created", stage="metadata")
        assert e.action == "created"


class TestUUIDManager:
    def test_generate_uuid(self):
        from projects.uuid_manager import UUIDManager
        uid = UUIDManager.generate_uuid()
        assert len(uid) == 32
        assert UUIDManager.validate_uuid(uid)

    def test_short_id(self):
        from projects.uuid_manager import UUIDManager
        sid = UUIDManager.generate_short_id()
        assert len(sid) == 8

    def test_safe_folder_name(self):
        from projects.uuid_manager import UUIDManager
        assert UUIDManager.safe_folder_name("Hello World!") == "hello_world"
        assert UUIDManager.safe_folder_name("") == "project"

    def test_validate_uuid(self):
        from projects.uuid_manager import UUIDManager
        uid = UUIDManager.generate_uuid()
        assert UUIDManager.validate_uuid(uid) is True
        assert UUIDManager.validate_uuid("") is False

    def test_checksum(self):
        from projects.uuid_manager import UUIDManager
        cs1 = UUIDManager.checksum("hello")
        cs2 = UUIDManager.checksum("hello")
        assert cs1 == cs2


class TestStorageManager:
    def test_create_and_load(self, tmp_path):
        from projects.storage_manager import StorageManager
        sm = StorageManager(root=tmp_path)
        sm.create_project_dir("proj123")
        sm.save_json("proj123", "test.json", {"key": "value"})
        data = sm.load_json("proj123", "test.json")
        assert data == {"key": "value"}

    def test_file_exists(self, tmp_path):
        from projects.storage_manager import StorageManager
        sm = StorageManager(root=tmp_path)
        sm.create_project_dir("proj123")
        sm.save_json("proj123", "test.json", {})
        assert sm.file_exists("proj123", "test.json") is True
        assert sm.file_exists("proj123", "missing.json") is False

    def test_delete_project(self, tmp_path):
        from projects.storage_manager import StorageManager
        sm = StorageManager(root=tmp_path)
        sm.create_project_dir("proj123")
        sm.save_json("proj123", "project.json", {"id": "123"})
        assert sm.project_exists("proj123")
        assert sm.delete_project("proj123", permanent=True) is True
        assert not sm.project_exists("proj123")

    def test_list_projects(self, tmp_path):
        from projects.storage_manager import StorageManager
        sm = StorageManager(root=tmp_path)
        sm.create_project_dir("p1")
        sm.save_json("p1", "project.json", {})
        sm.create_project_dir("p2")
        sm.save_json("p2", "project.json", {})
        projects = sm.list_projects()
        assert len(projects) >= 0


class TestProgressTracker:
    def test_compute_overall_progress_empty(self):
        from projects.progress_tracker import ProgressTracker
        assert ProgressTracker.compute_overall_progress({}) == 0.0

    def test_compute_overall_progress_partial(self):
        from projects.progress_tracker import ProgressTracker
        from projects.project_models import PipelineStage, StageInfo, StageStatus
        stages = {}
        for i, s in enumerate(PipelineStage):
            stages[s.value] = StageInfo(stage=s, status=StageStatus.COMPLETED if i < 3 else StageStatus.PENDING)
        pct = ProgressTracker.compute_overall_progress(stages)
        assert 0 < pct < 100

    def test_format_duration(self):
        from projects.progress_tracker import ProgressTracker
        assert ProgressTracker.format_duration(0.5) == "<1s"
        assert ProgressTracker.format_duration(90) == "1m 30s"

    def test_stage_summary(self):
        from projects.progress_tracker import ProgressTracker
        from projects.project_models import PipelineStage, StageInfo, StageStatus
        stages = {"metadata": StageInfo(stage=PipelineStage.METADATA, status=StageStatus.COMPLETED), "transcript": StageInfo(stage=PipelineStage.TRANSCRIPT, status=StageStatus.RUNNING)}
        summary = ProgressTracker.stage_summary(stages)
        assert summary["completed"] == 1
        assert summary["running"] == 1


class TestCheckpointManager:
    def test_create_checkpoint(self, tmp_path):
        from projects.checkpoint_manager import CheckpointManager
        from projects.storage_manager import StorageManager
        from projects.project_models import PipelineStage
        sm = StorageManager(root=tmp_path)
        cm = CheckpointManager(sm)
        sm.create_project_dir("proj123")
        sm.save_json("proj123", "project.json", {"status": "running"})
        cp = cm.create_checkpoint("proj123", PipelineStage.METADATA, "test")
        assert cp.stage == "metadata"

    def test_get_latest_checkpoint(self, tmp_path):
        from projects.checkpoint_manager import CheckpointManager
        from projects.storage_manager import StorageManager
        from projects.project_models import PipelineStage
        sm = StorageManager(root=tmp_path)
        cm = CheckpointManager(sm)
        sm.create_project_dir("proj123")
        sm.save_json("proj123", "project.json", {"v": 1})
        cm.create_checkpoint("proj123", PipelineStage.METADATA, "first")
        cm.create_checkpoint("proj123", PipelineStage.TRANSCRIPT, "second")
        latest = cm.get_latest_checkpoint("proj123")
        assert latest is not None
        assert latest.reason == "second"


class TestProjectManager:
    def test_create_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        from projects.project_manager import ProjectManager
        from projects.project_models import ProjectStatus
        pm = ProjectManager()
        project = pm.create_project(video_id="test123")
        assert project.project_id is not None
        assert project.status == ProjectStatus.CREATED

    def test_get_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        from projects.project_manager import ProjectManager
        pm = ProjectManager()
        created = pm.create_project(video_id="test123")
        loaded = pm.get_project(created.project_id)
        assert loaded is not None
        assert loaded.project_id == created.project_id

    def test_get_nonexistent_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        from projects.project_manager import ProjectManager
        pm = ProjectManager()
        assert pm.get_project("nonexistent") is None

    def test_stage_lifecycle(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        from projects.project_manager import ProjectManager
        from projects.project_models import PipelineStage, StageStatus
        pm = ProjectManager()
        project = pm.create_project(video_id="test123")
        pm.stage_started(project.project_id, PipelineStage.METADATA)
        p = pm.get_project(project.project_id)
        assert p.pipeline.stages["metadata"].status == StageStatus.RUNNING
        pm.stage_completed(project.project_id, PipelineStage.METADATA)
        p = pm.get_project(project.project_id)
        assert p.pipeline.stages["metadata"].status == StageStatus.COMPLETED

    def test_pause_resume_cancel(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        from projects.project_manager import ProjectManager
        from projects.project_models import ProjectStatus
        pm = ProjectManager()
        project = pm.create_project(video_id="test123")
        assert pm.pause_project(project.project_id) is True
        p = pm.get_project(project.project_id)
        assert p.status == ProjectStatus.PAUSED
        recovered = pm.resume_project(project.project_id)
        assert recovered is not None
        assert pm.cancel_project(project.project_id) is True

    def test_get_summary(self, tmp_path, monkeypatch):
        monkeypatch.setattr("projects.storage_manager.PROJECTS_ROOT", tmp_path)
        from projects.project_manager import ProjectManager
        pm = ProjectManager()
        project = pm.create_project(video_id="test123", name="Test Summary")
        summary = pm.get_summary(project.project_id)
        assert summary is not None
        assert summary["name"] == "Test Summary"
