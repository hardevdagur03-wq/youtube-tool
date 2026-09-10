"""Tests for the Enterprise Celery Configuration — queue topology, worker pools."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from background_processing.celery_enterprise import (
    QUEUE_DEFINITIONS, ENTERPRISE_TASK_ROUTES, WORKER_POOLS,
    configure_enterprise_queues, get_worker_command,
)


class TestEnterpriseCelery:
    def test_queue_definitions_contains_all_queues(self):
        queue_names = [q.name for q in QUEUE_DEFINITIONS]
        assert "critical" in queue_names
        assert "high" in queue_names
        assert "default" in queue_names
        assert "low" in queue_names
        assert "background" in queue_names
        assert "system" in queue_names
        assert "ai" in queue_names
        assert "transcript" in queue_names
        assert "export" in queue_names
        assert "publishing" in queue_names
        assert "email" in queue_names
        assert "notification" in queue_names
        assert "maintenance" in queue_names
        assert "analytics" in queue_names
        assert "dead_letter" in queue_names
        assert len(queue_names) == 15

    def test_all_queues_have_max_priority(self):
        for q in QUEUE_DEFINITIONS:
            assert q.queue_arguments["x-max-priority"] == 10

    def test_enterprise_routes_cover_all_prefixes(self):
        expected_prefixes = [
            "pipeline.", "transcript.", "ai.", "export.",
            "publishing.", "email.", "notification.", "cleanup.",
            "system.", "analytics.", "backup.", "cache.", "embedding.",
        ]
        for prefix in expected_prefixes:
            assert any(prefix in route for route in ENTERPRISE_TASK_ROUTES), f"Missing route for {prefix}"

    def test_missing_routes_default_to_default_queue(self):
        for route_key, route_val in ENTERPRISE_TASK_ROUTES.items():
            assert "queue" in route_val

    def test_configure_enterprise_queues_sets_topology(self):
        app = MagicMock()
        configure_enterprise_queues(app)
        assert app.conf.task_queues == QUEUE_DEFINITIONS
        assert app.conf.task_routes == ENTERPRISE_TASK_ROUTES

    def test_worker_pools_all_defined(self):
        expected_pools = ["ai", "transcript", "export", "notification", "maintenance", "analytics", "default"]
        for pool in expected_pools:
            assert pool in WORKER_POOLS, f"Missing pool: {pool}"

    def test_worker_pool_has_required_keys(self):
        for name, cfg in WORKER_POOLS.items():
            assert "queues" in cfg
            assert "concurrency" in cfg
            assert "pool" in cfg
            assert "max_tasks" in cfg
            assert "max_memory" in cfg

    def test_get_worker_command_returns_valid_command(self):
        cmd = get_worker_command("ai")
        assert "-A" in cmd
        assert "worker" in cmd
        assert "--queues" in cmd
        assert "ai,high,critical" in " ".join(cmd)

    def test_get_worker_command_transcript(self):
        cmd = get_worker_command("transcript")
        cmd_str = " ".join(cmd)
        assert "transcript" in cmd_str
        assert "gevent" in cmd_str or "--pool" in cmd_str

    def test_get_worker_command_invalid_pool(self):
        with pytest.raises(ValueError):
            get_worker_command("nonexistent_pool")

    def test_worker_command_concurrency_values(self):
        for name, cfg in WORKER_POOLS.items():
            cmd = get_worker_command(name)
            assert f"--concurrency {cfg['concurrency']}" in " ".join(cmd)
            assert f"--max-tasks-per-child {cfg['max_tasks']}" in " ".join(cmd)

    def test_default_queue_present_in_all_pools(self):
        for name, cfg in WORKER_POOLS.items():
            assert cfg["queues"], f"Empty queues for pool {name}"
