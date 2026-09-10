"""Tests for the Checkpoint Manager."""

from __future__ import annotations

from production_pipeline.checkpoint_manager import CheckpointManager


class TestCheckpointManager:
    def setup_method(self):
        self.cm = CheckpointManager()

    def test_save_checkpoint(self):
        cp = self.cm.save_checkpoint("e1", "metadata", 0, {"url": "x"}, {"title": "Test"})
        assert cp.stage_name == "metadata"
        assert cp.stage_index == 0
        assert cp.checkpoint_id is not None
        assert cp.input_hash is not None
        assert cp.output_hash is not None

    def test_get_last_checkpoint(self):
        self.cm.save_checkpoint("e1", "metadata", 0, {}, {"title": "T1"})
        self.cm.save_checkpoint("e1", "transcript", 1, {}, {"text": "T2"})
        last = self.cm.get_last_checkpoint("e1")
        assert last.stage_name == "transcript"

    def test_get_last_checkpoint_none(self):
        result = self.cm.get_last_checkpoint("nonexistent")
        assert result is None

    def test_get_checkpoint(self):
        self.cm.save_checkpoint("e1", "metadata", 0, {}, {"r": "x"})
        cp = self.cm.get_checkpoint("e1", "metadata")
        assert cp is not None
        assert cp.stage_name == "metadata"

    def test_get_checkpoint_not_found(self):
        result = self.cm.get_checkpoint("e1", "nonexistent")
        assert result is None

    def test_list_checkpoints(self):
        self.cm.save_checkpoint("e1", "a", 0, {}, {})
        self.cm.save_checkpoint("e1", "b", 1, {}, {})
        cps = self.cm.list_checkpoints("e1")
        assert len(cps) == 2

    def test_list_checkpoints_empty(self):
        cps = self.cm.list_checkpoints("nonexistent")
        assert cps == []

    def test_get_completed_stages(self):
        self.cm.save_checkpoint("e1", "a", 0, {}, {})
        self.cm.save_checkpoint("e1", "b", 1, {}, {})
        stages = self.cm.get_completed_stages("e1")
        assert stages == ["a", "b"]

    def test_rebuild_pipeline_state(self):
        self.cm.save_checkpoint("e1", "metadata", 0, {}, {"title": "Test"})
        self.cm.save_checkpoint("e1", "transcript", 1, {}, {"text": "Hello"})
        ctx = self.cm.rebuild_pipeline_state("e1")
        assert ctx["metadata"]["title"] == "Test"
        assert ctx["transcript"]["text"] == "Hello"

    def test_rebuild_empty(self):
        ctx = self.cm.rebuild_pipeline_state("nonexistent")
        assert ctx == {}

    def test_verify_checkpoint_passes(self):
        cp = self.cm.save_checkpoint("e1", "a", 0, {}, {"d": 1})
        assert self.cm.verify_checkpoint(cp) == True

    def test_verify_checkpoint_fails_on_tamper(self):
        cp = self.cm.save_checkpoint("e1", "a", 0, {}, {"d": 1})
        cp.output_data = {"d": 999}
        assert self.cm.verify_checkpoint(cp) == False

    def test_delete_checkpoints(self):
        self.cm.save_checkpoint("e1", "a", 0, {}, {})
        self.cm.delete_checkpoints("e1")
        assert self.cm.get_completed_stages("e1") == []

    def test_checkpoint_count(self):
        self.cm.save_checkpoint("e1", "a", 0, {}, {})
        self.cm.save_checkpoint("e1", "b", 1, {}, {})
        assert self.cm.checkpoint_count("e1") == 2

    def test_hash_consistency(self):
        cp1 = self.cm.save_checkpoint("e1", "a", 0, {"input": 1}, {"output": 1})
        cp2 = self.cm.save_checkpoint("e2", "a", 0, {"input": 1}, {"output": 1})
        assert cp1.input_hash == cp2.input_hash
        assert cp1.output_hash == cp2.output_hash

    def test_hash_different_inputs(self):
        cp1 = self.cm.save_checkpoint("e1", "a", 0, {"input": 1}, {"output": 1})
        cp2 = self.cm.save_checkpoint("e1", "a", 0, {"input": 2}, {"output": 1})
        assert cp1.input_hash != cp2.input_hash

    def test_duration_tracking(self):
        cp = self.cm.save_checkpoint("e1", "a", 0, {}, {}, duration_ms=1500.0)
        assert cp.duration_ms == 1500.0

    def test_retry_count_tracking(self):
        cp = self.cm.save_checkpoint("e1", "a", 0, {}, {}, retry_count=3)
        assert cp.retry_count == 3

    def test_multiple_executions_independent(self):
        self.cm.save_checkpoint("e1", "a", 0, {}, {})
        self.cm.save_checkpoint("e2", "b", 0, {}, {})
        assert self.cm.checkpoint_count("e1") == 1
        assert self.cm.checkpoint_count("e2") == 1

    def test_stage_index_ordering(self):
        self.cm.save_checkpoint("e1", "b", 1, {}, {})
        self.cm.save_checkpoint("e1", "a", 0, {}, {})
        stages = self.cm.get_completed_stages("e1")
        assert stages == ["b", "a"]
