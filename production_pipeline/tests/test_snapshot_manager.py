"""Tests for the Snapshot Manager."""

from __future__ import annotations

from production_pipeline.snapshot_manager import SnapshotManager


class TestSnapshotManager:
    def setup_method(self):
        self.sm = SnapshotManager()

    def test_create_snapshot(self):
        snap = self.sm.create_snapshot("e1", "metadata", {"url": "x"}, {"title": "Test"})
        assert snap.stage_name == "metadata"
        assert snap.content_hash is not None
        assert len(snap.content_hash) == 64  # SHA-256 hex

    def test_create_snapshot_with_all_fields(self):
        snap = self.sm.create_snapshot(
            "e1", "analysis", {"text": "input"}, {"result": "output"},
            prompt="Analyze this", model="gpt-4", provider="openai",
            temperature=0.5, generated_files=["/tmp/file.txt"],
            metrics={"tokens": 100}, logs=["Starting analysis"],
        )
        assert snap.prompt == "Analyze this"
        assert snap.model == "gpt-4"
        assert snap.provider == "openai"
        assert snap.temperature == 0.5

    def test_get_snapshot(self):
        self.sm.create_snapshot("e1", "metadata", {}, {})
        snap = self.sm.get_snapshot("e1", "metadata")
        assert snap is not None
        assert snap.stage_name == "metadata"

    def test_get_snapshot_not_found(self):
        result = self.sm.get_snapshot("e1", "nonexistent")
        assert result is None

    def test_get_snapshot_by_hash(self):
        snap = self.sm.create_snapshot("e1", "metadata", {}, {})
        found = self.sm.get_snapshot_by_hash(snap.content_hash)
        assert found is not None
        assert found.snapshot_id == snap.snapshot_id

    def test_get_snapshot_by_hash_not_found(self):
        result = self.sm.get_snapshot_by_hash("nonexistent_hash")
        assert result is None

    def test_list_snapshots(self):
        self.sm.create_snapshot("e1", "a", {}, {})
        self.sm.create_snapshot("e1", "b", {}, {})
        snaps = self.sm.list_snapshots("e1")
        assert len(snaps) == 2

    def test_verify_integrity_passes(self):
        self.sm.create_snapshot("e1", "metadata", {"i": 1}, {"o": 1})
        assert self.sm.verify_integrity("e1") == True

    def test_verify_integrity_by_stage(self):
        self.sm.create_snapshot("e1", "metadata", {"i": 1}, {"o": 1})
        assert self.sm.verify_integrity("e1", "metadata") == True
        assert self.sm.verify_integrity("e1", "nonexistent") == True

    def test_verify_integrity_fails_on_tamper(self):
        snap = self.sm.create_snapshot("e1", "metadata", {"i": 1}, {"o": 1})
        snap.outputs = {"o": 999}
        assert self.sm.verify_integrity("e1") == False

    def test_delete_snapshots(self):
        self.sm.create_snapshot("e1", "a", {}, {})
        self.sm.delete_snapshots("e1")
        assert self.sm.list_snapshots("e1") == []

    def test_get_snapshot_chain(self):
        self.sm.create_snapshot("e1", "a", {}, {})
        self.sm.create_snapshot("e1", "b", {}, {})
        chain = self.sm.get_snapshot_chain("e1")
        assert len(chain) == 2
        assert chain[0]["stage_name"] == "a"
        assert chain[1]["stage_name"] == "b"

    def test_snapshot_chain_contains_metadata(self):
        self.sm.create_snapshot("e1", "a", {}, {}, model="gpt-4", provider="openai")
        chain = self.sm.get_snapshot_chain("e1")
        assert chain[0]["model"] == "gpt-4"
        assert chain[0]["provider"] == "openai"

    def test_multiple_executions_independent(self):
        self.sm.create_snapshot("e1", "a", {}, {})
        self.sm.create_snapshot("e2", "a", {}, {})
        assert len(self.sm.list_snapshots("e1")) == 1
        assert len(self.sm.list_snapshots("e2")) == 1

    def test_content_hash_deterministic(self):
        snap1 = self.sm.create_snapshot("e1", "a", {"i": 1}, {"o": 1})
        snap2 = self.sm.create_snapshot("e2", "a", {"i": 1}, {"o": 1})
        assert snap1.content_hash == snap2.content_hash

    def test_content_hash_changes_with_input(self):
        snap1 = self.sm.create_snapshot("e1", "a", {"i": 1}, {"o": 1})
        snap2 = self.sm.create_snapshot("e1", "a", {"i": 2}, {"o": 1})
        assert snap1.content_hash != snap2.content_hash

    def test_empty_snapshot(self):
        snap = self.sm.create_snapshot("e1", "empty", {}, {})
        assert snap.content_hash is not None
        assert snap.generated_files == []
        assert snap.metrics == {}
        assert snap.logs == []
