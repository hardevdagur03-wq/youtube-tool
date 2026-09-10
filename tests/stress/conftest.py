from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def stress_config() -> dict[str, Any]:
    return {
        "max_concurrent_pipelines": 50,
        "max_queue_depth": 10_000,
        "sustained_load_duration_s": 60,
        "recovery_sla_s": 30,
        "memory_leak_threshold_mb": 100,
        "connection_pool_size": 20,
    }
