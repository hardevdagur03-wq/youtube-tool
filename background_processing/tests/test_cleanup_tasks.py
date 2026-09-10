"""Tests for Cleanup Tasks — Celery tasks for maintenance and health checks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from background_processing.job_repository import JobRepository


class TestCleanupTasks:

    def _mock_session(self):
        s = MagicMock()
        s.__aenter__ = AsyncMock(return_value=s)
        s.__aexit__ = AsyncMock(return_value=None)
        return s

    def test_cleanup_stale_jobs(self):
        from background_processing.tasks.cleanup_tasks import cleanup_stale_jobs

        old_job = MagicMock()
        old_job.uuid = "stale-job-1"
        old_job.started_at = datetime.now(timezone.utc) - timedelta(hours=2)
        old_job.status = "running"
        old_job.attempts = 1

        mock_repo = MagicMock()
        mock_repo.find_stuck_jobs = AsyncMock(return_value=[old_job])
        mock_repo.update = AsyncMock(return_value=old_job)

        with patch("background_processing.tasks.cleanup_tasks.JobRepository", return_value=mock_repo):
            with patch("database.db_session.db_manager") as mock_mgr:
                mock_mgr.session_factory.return_value = self._mock_session()
                task = cleanup_stale_jobs
                task.push_request(args=(30,), kwargs={})
                try:
                    result = task(30)
                    assert result["recovered"] == 1
                finally:
                    task.pop_request()

    def test_cleanup_expired_results(self):
        from background_processing.tasks.cleanup_tasks import cleanup_expired_results

        mock_execute = MagicMock()
        mock_execute.rowcount = 5
        session = self._mock_session()
        session.execute = AsyncMock(return_value=mock_execute)
        session.commit = AsyncMock()

        with patch("database.db_session.db_manager") as mock_mgr:
            mock_mgr.session_factory.return_value = session
            task = cleanup_expired_results
            task.push_request(args=(7,), kwargs={})
            try:
                result = task(7)
                assert result["deleted"] == 5
            finally:
                task.pop_request()

    def test_system_health_check(self):
        from background_processing.tasks.cleanup_tasks import system_health_check

        mock_repo = MagicMock()
        mock_repo.get_metrics = AsyncMock(return_value={"total": 10, "by_status": {}, "by_type": {}, "avg_duration_ms": 0})

        with patch("background_processing.tasks.cleanup_tasks.JobRepository", return_value=mock_repo):
            with patch("database.db_session.db_manager") as mock_mgr:
                mock_mgr.session_factory.return_value = self._mock_session()
                with patch("background_processing.tasks.cleanup_tasks._get_db") as mock_db:
                    mock_db.return_value.health_check = AsyncMock(return_value={"healthy": True})
                    with patch("background_processing.config.BackgroundProcessingConfig") as mock_cfg_cls:
                        mock_cfg = MagicMock()
                        mock_cfg.redis_url = "redis://localhost:6379/0"
                        mock_cfg_cls.from_env.return_value = mock_cfg
                        task = system_health_check
                        task.push_request(args=(), kwargs={})
                        try:
                            result = task()
                            assert isinstance(result, dict)
                        finally:
                            task.pop_request()

    def test_dlq_cleanup(self):
        from background_processing.tasks.cleanup_tasks import dlq_cleanup

        with patch("background_processing.tasks.cleanup_tasks.DeadLetterQueue") as mock_dlq_cls:
            mock_dlq = AsyncMock()
            mock_dlq.count = AsyncMock(return_value=3)
            mock_dlq.list = AsyncMock(return_value=[MagicMock(), MagicMock()])
            mock_dlq_cls.return_value = mock_dlq
            task = dlq_cleanup
            task.push_request(args=(604800,), kwargs={})
            try:
                result = task(604800)
                assert result["current_size"] == 3
            finally:
                task.pop_request()

    def test_backup_job_history(self):
        from background_processing.tasks.cleanup_tasks import backup_job_history
        task = backup_job_history
        task.push_request(args=(90,), kwargs={})
        try:
            result = task(90)
            assert result["archived"] == 0
            assert "placeholder" in result["note"]
        finally:
            task.pop_request()
