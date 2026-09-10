"""Tests for the Workflow Engine — pipeline orchestration, chains, resume."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from background_processing.models import JobCreate
from background_processing.workflow_engine import (
    WorkflowDefinition, WorkflowEngine, WorkflowStatus, WorkflowStep,
)


class TestWorkflowEngine:
    @pytest_asyncio.fixture
    async def engine(self, job_repo, mock_redis):
        dispatcher = AsyncMock()
        dispatcher.dispatch = AsyncMock()
        dispatcher.dispatch.return_value.model_dump.return_value = {"status": "queued"}
        from background_processing.celery_app import get_celery_app
        eng = WorkflowEngine(
            dispatcher=dispatcher,
            job_repo=job_repo,
            celery_app=get_celery_app(),
        )
        eng._save_checkpoint = AsyncMock()
        eng._load_checkpoint = AsyncMock(return_value=None)
        yield eng

    async def test_execute_sequential_workflow(self, engine):
        workflow = WorkflowDefinition(
            workflow_id="wf-1",
            name="test-workflow",
            project_id="proj-1",
            steps=[
                WorkflowStep(name="step1", job_type="pipeline.metadata"),
                WorkflowStep(name="step2", job_type="pipeline.analysis"),
                WorkflowStep(name="step3", job_type="pipeline.seo"),
            ],
        )
        execution = await engine.execute(workflow)
        assert execution.status == WorkflowStatus.COMPLETED
        assert len(execution.completed_steps) == 3
        assert execution.current_step == "step3"

    async def test_execute_empty_workflow(self, engine):
        workflow = WorkflowDefinition(
            workflow_id="wf-empty",
            name="empty",
            project_id="proj-1",
            steps=[],
        )
        execution = await engine.execute(workflow)
        assert execution.status == WorkflowStatus.COMPLETED

    async def test_execute_single_step(self, engine):
        workflow = WorkflowDefinition(
            workflow_id="wf-single",
            name="single",
            project_id="proj-1",
            steps=[WorkflowStep(name="only", job_type="pipeline.metadata")],
        )
        execution = await engine.execute(workflow)
        assert execution.status == WorkflowStatus.COMPLETED
        assert len(execution.completed_steps) == 1

    async def test_execution_tracking(self, engine):
        workflow = WorkflowDefinition(
            workflow_id="wf-track",
            name="tracking",
            project_id="proj-1",
            steps=[WorkflowStep(name="s1", job_type="pipeline.a")],
        )
        execution = await engine.execute(workflow)
        fetched = await engine.get_execution(execution.execution_id)
        assert fetched is not None
        assert fetched.status == WorkflowStatus.COMPLETED

    async def test_cancel_execution(self, engine):
        workflow = WorkflowDefinition(
            workflow_id="wf-cancel",
            name="cancel-test",
            project_id="proj-1",
            steps=[WorkflowStep(name="s1", job_type="pipeline.a")],
        )
        execution = await engine.execute(workflow)
        result = await engine.cancel(execution.execution_id)
        assert result is True

    async def test_list_executions(self, engine):
        wf = WorkflowDefinition(workflow_id="proj-list-1", name="list-test", project_id="proj-list-1", steps=[])
        await engine.execute(wf)
        all_execs = await engine.list_executions()
        assert len(all_execs) >= 1

    async def test_list_executions_by_project(self, engine):
        wf = WorkflowDefinition(workflow_id="proj-filter", name="filter-test", project_id="proj-filter", steps=[])
        await engine.execute(wf)
        execs = await engine.list_executions(project_id="proj-filter")
        assert len(execs) >= 1

    async def test_pipeline_build_and_run(self, engine, mock_redis):
        execution = await engine.run_pipeline(
            project_id="proj-pipe-1",
            payload={"url": "https://youtube.com/watch?v=test"},
            start_from="",
        )
        assert execution.status in (WorkflowStatus.COMPLETED, WorkflowStatus.RUNNING)

    async def test_pipeline_resume_from_checkpoint(self, engine):
        engine._load_checkpoint = AsyncMock(return_value={"last_stage": "pipeline.analysis"})
        execution = await engine.resume(
            project_id="proj-resume-1",
            payload={},
        )
        assert execution is not None

    async def test_pipeline_resume_no_checkpoint_starts_fresh(self, engine):
        engine._load_checkpoint = AsyncMock(return_value=None)
        execution = await engine.resume(
            project_id="proj-fresh-1",
            payload={},
        )
        assert execution is not None

    async def test_clear_checkpoint(self, engine, mock_redis):
        await engine._save_checkpoint("proj-clear", "stage1")
        await engine.clear_checkpoint("proj-clear")
        checkpoint = await engine._load_checkpoint("proj-clear")
        assert checkpoint is None
