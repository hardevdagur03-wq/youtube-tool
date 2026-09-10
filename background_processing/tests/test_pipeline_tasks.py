"""Tests for Pipeline Tasks — Celery task wrappers for pipeline stages.

Uses mocked DatabaseService to avoid actual database calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_db():
    """Mock DatabaseService and ProgressEmitter for all pipeline task tests."""
    mock_emitter = MagicMock(
        on_started=AsyncMock(),
        on_progress=AsyncMock(),
        on_completed=AsyncMock(return_value=None),
        on_failed=AsyncMock(),
        on_stage_completed=AsyncMock(),
    )

    mock_session = MagicMock(
        __aenter__=AsyncMock(return_value=MagicMock()),
        __aexit__=AsyncMock(return_value=None),
    )

    with patch("background_processing.tasks.pipeline_tasks.ProgressEmitter", return_value=mock_emitter):
        with patch("database.db_session.db_manager") as mock_mgr:
            mock_mgr.session_factory.return_value = mock_session
            with patch("background_processing.tasks.pipeline_tasks._get_db") as mock:
                instance = AsyncMock()
                instance.save_video = AsyncMock(return_value={"video_id": "v1"})
                instance.save_analysis = AsyncMock(return_value={"summary": "test"})
                instance.save_knowledge_graph = AsyncMock(return_value={"entities": []})
                instance.save_seo = AsyncMock(return_value={"seo_score": 85})
                instance.save_outline = AsyncMock(return_value={"title": "Test"})
                instance.save_sections = AsyncMock(return_value=[])
                instance.save_draft = AsyncMock(return_value={"content": "draft"})
                instance.save_review = AsyncMock(return_value={"score": 8})
                instance.save_optimization = AsyncMock(return_value={"round": 1})
                instance.save_export = AsyncMock(return_value={"format": "md"})
                instance.stage_completed = AsyncMock()
                instance.complete_project = AsyncMock(return_value=True)
                instance.get_transcript = AsyncMock(return_value={"text": "transcript"})
                mock.return_value = instance
                yield instance


class TestPipelineTasks:
    def test_process_video(self, mock_db):
        from background_processing.tasks.pipeline_tasks import process_video
        task = process_video
        task.push_request(args=("proj-1", "job-1"), kwargs={"url": "https://youtube.com/watch?v=abc"})
        try:
            result = task("proj-1", "job-1", url="https://youtube.com/watch?v=abc")
        finally:
            task.pop_request()

    def test_generate_analysis(self, mock_db):
        from background_processing.tasks.pipeline_tasks import generate_analysis
        task = generate_analysis
        task.push_request(args=("proj-1", "job-1"), kwargs={"summary": "Test summary", "topics": ["AI", "ML"]})
        try:
            result = task("proj-1", "job-1", summary="Test summary", topics=["AI", "ML"])
        finally:
            task.pop_request()

    def test_generate_knowledge_graph(self, mock_db):
        from background_processing.tasks.pipeline_tasks import generate_knowledge_graph
        task = generate_knowledge_graph
        task.push_request(args=("proj-1", "job-1"), kwargs={})
        try:
            result = task("proj-1", "job-1", entities=[{"name": "AI"}], relationships=[])
        finally:
            task.pop_request()

    def test_generate_seo_analysis(self, mock_db):
        from background_processing.tasks.pipeline_tasks import generate_seo_analysis
        task = generate_seo_analysis
        task.push_request(args=("proj-1", "job-1"), kwargs={"seo_score": 90})
        try:
            result = task("proj-1", "job-1", seo_score=90, primary_keyword="AI", meta_description="desc")
        finally:
            task.pop_request()

    def test_generate_outline(self, mock_db):
        from background_processing.tasks.pipeline_tasks import generate_outline
        task = generate_outline
        task.push_request(args=("proj-1", "job-1"), kwargs={"title": {"primary_title": "Test"}, "sections": []})
        try:
            result = task("proj-1", "job-1", title={"primary_title": "Test"}, sections=[])
        finally:
            task.pop_request()

    def test_generate_sections(self, mock_db):
        from background_processing.tasks.pipeline_tasks import generate_sections
        task = generate_sections
        sections = [{"heading": "Intro", "content": "Hello world", "order": 1}]
        task.push_request(args=("proj-1", "job-1"), kwargs={"sections": sections})
        try:
            result = task("proj-1", "job-1", sections=sections)
        finally:
            task.pop_request()

    def test_generate_draft(self, mock_db):
        from background_processing.tasks.pipeline_tasks import generate_draft
        task = generate_draft
        task.push_request(args=("proj-1", "job-1"), kwargs={"markdown_content": "# Hello", "word_count": 100})
        try:
            result = task("proj-1", "job-1", markdown_content="# Hello", word_count=100)
        finally:
            task.pop_request()

    def test_generate_review(self, mock_db):
        from background_processing.tasks.pipeline_tasks import generate_review
        task = generate_review
        task.push_request(args=("proj-1", "job-1"), kwargs={"overall_score": 85})
        try:
            result = task("proj-1", "job-1", overall_score=85, issues=[], recommendations=[])
        finally:
            task.pop_request()

    def test_generate_optimization(self, mock_db):
        from background_processing.tasks.pipeline_tasks import generate_optimization
        task = generate_optimization
        task.push_request(args=("proj-1", "job-1"), kwargs={"optimization_round": 1})
        try:
            result = task("proj-1", "job-1", optimization_round=1, changes_applied=[])
        finally:
            task.pop_request()

    def test_generate_export(self, mock_db):
        from background_processing.tasks.pipeline_tasks import generate_export
        task = generate_export
        task.push_request(args=("proj-1", "job-1"), kwargs={"export_format": "markdown"})
        try:
            result = task("proj-1", "job-1", export_format="markdown", file_path="/tmp/test.md")
        finally:
            task.pop_request()

    def test_run_pipeline_stage_dispatch(self, mock_db):
        from background_processing.tasks.pipeline_tasks import run_pipeline_stage
        task = run_pipeline_stage
        task.push_request(args=("analyses", "proj-1", "job-1"), kwargs={})
        try:
            with patch("background_processing.tasks.pipeline_tasks.generate_analysis.delay") as mock_delay:
                run_pipeline_stage("analyses", "proj-1", "job-1")
                mock_delay.assert_called_once()
        finally:
            task.pop_request()

    def test_run_pipeline_stage_export_dispatch(self, mock_db):
        from background_processing.tasks.pipeline_tasks import run_pipeline_stage
        task = run_pipeline_stage
        task.push_request(args=("exports", "proj-1", "job-1"), kwargs={})
        try:
            with patch("background_processing.tasks.pipeline_tasks.generate_export.delay") as mock_delay:
                run_pipeline_stage("exports", "proj-1", "job-1")
                mock_delay.assert_called_once()
        finally:
            task.pop_request()

    def test_run_pipeline_stage_unknown(self, mock_db):
        from background_processing.tasks.pipeline_tasks import run_pipeline_stage
        task = run_pipeline_stage
        task.push_request(args=("unknown", "proj-1", "job-1"), kwargs={})
        try:
            with pytest.raises(ValueError, match="Unknown pipeline stage"):
                run_pipeline_stage("unknown", "proj-1", "job-1")
        finally:
            task.pop_request()
