"""Tests for the Recovery Manager, Resume Engine, and Workflow Engine."""

from __future__ import annotations

import asyncio
import time

from production_pipeline.recovery_manager import RecoveryManager
from production_pipeline.resume_engine import ResumeEngine
from production_pipeline.checkpoint_manager import CheckpointManager
from production_pipeline.workflow import DurableWorkflowEngine
from production_pipeline.constants import STAGE_NAMES


class TestRecoveryManager:
    def test_scan_empty(self):
        rm = RecoveryManager()
        results = rm.scan_and_recover({})
        assert results == []

    def test_scan_no_recovery_needed(self):
        rm = RecoveryManager()
        results = rm.scan_and_recover({"e1": {"workflow_state": "completed"}})
        assert results == []

    def test_scan_recovery_needed(self):
        rm = RecoveryManager()
        results = rm.scan_and_recover({"e1": {"workflow_state": "running", "started_at": "2020-01-01T00:00:00"}})
        assert len(results) == 1

    def test_recover_execution(self):
        rm = RecoveryManager()
        result = rm.recover_execution("e1", {"workflow_state": "running"})
        assert result["execution_id"] == "e1"
        assert result["previous_state"] == "running"
        assert result["attempt"] == 1

    def test_recover_multiple_increments_attempt(self):
        rm = RecoveryManager()
        rm.recover_execution("e1", {"workflow_state": "failed"})
        result = rm.recover_execution("e1", {"workflow_state": "failed"})
        assert result["attempt"] == 2

    def test_mark_recovered(self):
        rm = RecoveryManager()
        rm.recover_execution("e1", {"workflow_state": "running"})
        rm.mark_recovered("e1")
        history = rm.get_recovery_history("e1")
        assert history[0]["recovered_state"] == "running"

    def test_mark_failed(self):
        rm = RecoveryManager()
        rm.recover_execution("e1", {"workflow_state": "running"})
        rm.mark_failed("e1", "could not recover")
        history = rm.get_recovery_history("e1")
        assert history[0]["error"] == "could not recover"

    def test_get_recovery_history_empty(self):
        rm = RecoveryManager()
        assert rm.get_recovery_history("nonexistent") == []

    def test_get_recovery_summary(self):
        rm = RecoveryManager()
        rm.recover_execution("e1", {"workflow_state": "running"})
        rm.mark_recovered("e1")
        summary = rm.get_recovery_summary()
        assert summary["total_recoveries"] >= 1


class TestResumeEngine:
    def setup_method(self):
        self.cm = CheckpointManager()
        self.re = ResumeEngine(self.cm)

    def test_find_resumable_empty(self):
        results = self.re.find_resumable_workflows({})
        assert results == []

    def test_find_resumable_none(self):
        results = self.re.find_resumable_workflows({"e1": {"workflow_state": "completed"}})
        assert results == []

    def test_find_resumable_with_checkpoints(self):
        self.cm.save_checkpoint("e1", "metadata", 0, {}, {})
        results = self.re.find_resumable_workflows({"e1": {"workflow_state": "failed"}})
        assert len(results) == 1

    def test_determine_next_stage_first(self):
        next_stage = self.re.determine_next_stage("e1")
        assert next_stage == "metadata"

    def test_determine_next_stage_after_metadata(self):
        self.cm.save_checkpoint("e1", "metadata", 0, {}, {})
        next_stage = self.re.determine_next_stage("e1")
        assert next_stage == "transcript"

    def test_determine_next_stage_all_complete(self):
        for i, s in enumerate(STAGE_NAMES):
            self.cm.save_checkpoint("e1", s, i, {}, {})
        next_stage = self.re.determine_next_stage("e1")
        assert next_stage is None

    def test_rebuild_context(self):
        self.cm.save_checkpoint("e1", "metadata", 0, {}, {"title": "Test"})
        ctx = self.re.rebuild_context("e1")
        assert ctx["metadata"]["title"] == "Test"

    def test_resume(self):
        self.cm.save_checkpoint("e1", "metadata", 0, {}, {"title": "T"})
        result = self.re.resume("e1", {"workflow_state": "failed"})
        assert result["status"] == "resumed"
        assert result["next_stage"] == "transcript"
        assert result["completed_count"] == 1

    def test_resume_all_complete(self):
        for i, s in enumerate(STAGE_NAMES):
            self.cm.save_checkpoint("e1", s, i, {}, {})
        result = self.re.resume("e1", {"workflow_state": "running"})
        assert result["status"] == "already_completed"

    def test_get_resume_point(self):
        self.cm.save_checkpoint("e1", "metadata", 0, {}, {})
        cp = self.re.get_resume_point("e1")
        assert cp.stage_name == "metadata"

    def test_has_completed_stage_true(self):
        self.cm.save_checkpoint("e1", "metadata", 0, {}, {})
        assert self.re.has_completed_stage("e1", "metadata") == True

    def test_has_completed_stage_false(self):
        assert self.re.has_completed_stage("e1", "analysis") == False


class TestDurableWorkflowEngine:
    def test_create_engine(self):
        engine = DurableWorkflowEngine()
        assert engine is not None

    def test_register_stage_executor(self):
        engine = DurableWorkflowEngine()
        engine.register_stage_executor("metadata", lambda ctx: None)
        assert "metadata" in engine._stage_executors

    def test_run_empty_workflow(self):
        engine = DurableWorkflowEngine()
        async def mock_fn(ctx):
            return {"r": "ok"}
        engine.register_stage_executor("metadata", mock_fn)
        result = asyncio.run(engine.run_workflow("e1", stages=["metadata"]))
        assert result["success"] == True
        assert result["execution_id"] == "e1"

    def test_run_with_stages(self):
        engine = DurableWorkflowEngine()
        async def mock_meta(ctx):
            return {"title": "Test"}
        engine.register_stage_executor("metadata", mock_meta)
        result = asyncio.run(engine.run_workflow("e1", stages=["metadata"]))
        assert result["success"] == True
        assert "metadata" in result["completed_stages"]

    def test_run_multiple_stages(self):
        engine = DurableWorkflowEngine()
        async def mock_meta(ctx):
            return {"title": "Test"}
        async def mock_trans(ctx):
            return {"text": "Hello"}
        engine.register_stage_executor("metadata", mock_meta)
        engine.register_stage_executor("transcript", mock_trans)
        result = asyncio.run(engine.run_workflow("e1", stages=["metadata", "transcript"]))
        assert result["success"] == True
        assert len(result["completed_stages"]) == 2

    def test_idempotency_skip_on_rerun(self):
        engine = DurableWorkflowEngine()
        async def mock_meta(ctx):
            return {"title": "Test"}
        engine.register_stage_executor("metadata", mock_meta)
        asyncio.run(engine.run_workflow("e1", stages=["metadata"]))
        result = asyncio.run(engine.run_workflow("e1", stages=["metadata"]))
        assert result["success"] == True

    def test_workflow_status(self):
        engine = DurableWorkflowEngine()
        async def mock_fn(ctx):
            return {"result": "ok"}
        engine.register_stage_executor("metadata", mock_fn)
        asyncio.run(engine.run_workflow("e1", stages=["metadata"]))
        status = engine.get_workflow_status("e1")
        assert status is not None
        assert "completed_stages" in status

    def test_workflow_status_nonexistent(self):
        engine = DurableWorkflowEngine()
        assert engine.get_workflow_status("nonexistent") is None

    def test_cancel_workflow(self):
        engine = DurableWorkflowEngine()
        result = asyncio.run(engine.cancel_workflow("nonexistent"))
        assert result == False

    def test_resume_workflow(self):
        engine = DurableWorkflowEngine()
        async def mock_fn(ctx):
            return {"r": "ok"}
        engine.register_stage_executor("metadata", mock_fn)
        async def mock_fn2(ctx):
            return {"r": "ok2"}
        engine.register_stage_executor("transcript", mock_fn2)

        # Run first stage manually via checkpoint
        engine._checkpoints.save_checkpoint("e1", "metadata", 0, {}, {"r": "ok"})
        result = asyncio.run(engine.resume_workflow("e1"))
        assert result is not None

    def test_checkpoint_created_after_stage(self):
        engine = DurableWorkflowEngine()
        async def mock_fn(ctx):
            return {"r": "ok"}
        engine.register_stage_executor("metadata", mock_fn)
        asyncio.run(engine.run_workflow("e1", stages=["metadata"]))
        cps = engine._checkpoints.list_checkpoints("e1")
        assert len(cps) == 1
        assert cps[0].stage_name == "metadata"

    def test_events_logged_during_workflow(self):
        engine = DurableWorkflowEngine()
        async def mock_fn(ctx):
            return {"r": "ok"}
        engine.register_stage_executor("metadata", mock_fn)
        asyncio.run(engine.run_workflow("e1", stages=["metadata"]))
        events = engine._tx_log.get_events("e1")
        assert len(events) >= 3  # started, stage_started, stage_completed, completed
