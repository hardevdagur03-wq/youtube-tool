"""Tests for Export Tasks — Celery tasks for exporting pipeline outputs."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_db():
    with patch("background_processing.tasks.export_tasks._get_db") as mock:
        instance = AsyncMock()
        instance.get_draft = AsyncMock(return_value={
            "markdown_content": "# Test\n\nHello world",
            "html_content": "<h1>Test</h1>",
        })
        instance.get_project = AsyncMock(return_value={
            "name": "Test Project",
            "project_id": "proj-1",
        })
        instance.save_export = AsyncMock(return_value={
            "export_format": "markdown",
            "filename": "Test Project.md",
        })
        instance.log_event = AsyncMock()
        mock.return_value = instance
        yield instance


class TestExportTasks:
    def test_export_project_markdown(self, mock_db):
        from background_processing.tasks.export_tasks import export_project
        task = export_project
        task.push_request(args=("proj-1", "markdown"), kwargs={})
        try:
            result = task("proj-1", "markdown")
            assert result is not None
        finally:
            task.pop_request()

    def test_export_project_html(self, mock_db):
        from background_processing.tasks.export_tasks import export_project
        task = export_project
        task.push_request(args=("proj-1", "html"), kwargs={})
        try:
            result = task("proj-1", "html")
        finally:
            task.pop_request()

    def test_export_no_draft(self, mock_db):
        mock_db.get_draft.return_value = None
        from background_processing.tasks.export_tasks import export_project
        task = export_project
        task.push_request(args=("proj-1", "markdown"), kwargs={})
        try:
            with pytest.raises(ValueError, match="No draft found"):
                task("proj-1", "markdown")
        finally:
            task.pop_request()

    def test_batch_export(self, mock_db):
        from background_processing.tasks.export_tasks import batch_export
        task = batch_export
        task.push_request(args=(["proj-1", "proj-2"], "markdown"), kwargs={})
        try:
            result = task(["proj-1", "proj-2"], "markdown")
            assert len(result) == 2
            assert result[0]["status"] == "ok"
        finally:
            task.pop_request()

    def test_batch_export_partial_failure(self, mock_db):
        mock_db.get_draft.side_effect = [
            {"markdown_content": "# OK"},
            Exception("Project not found"),
        ]
        from background_processing.tasks.export_tasks import batch_export
        task = batch_export
        task.push_request(args=(["proj-1", "proj-2"], "markdown"), kwargs={})
        try:
            result = task(["proj-1", "proj-2"], "markdown")
            assert result[0]["status"] == "ok"
            assert result[1]["status"] == "error"
        finally:
            task.pop_request()
