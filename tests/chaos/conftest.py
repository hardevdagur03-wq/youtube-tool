from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def chaos_config() -> dict[str, Any]:
    return {
        "crash_recovery_timeout_s": 10,
        "redis_fallback_enabled": True,
        "db_recovery_timeout_s": 15,
        "llm_timeout_s": 5,
        "circuit_breaker_threshold": 5,
        "disk_full_simulation": False,
        "network_latency_ms": 500,
    }


@pytest.fixture
def fault_injector():
    class FaultInjector:
        def __init__(self):
            self._faults = {}

        def inject(self, service: str, fault_type: str, **kwargs):
            self._faults[service] = {"type": fault_type, "params": kwargs}
            return True

        def clear(self, service: str = None):
            if service:
                self._faults.pop(service, None)
            else:
                self._faults.clear()

        def has_fault(self, service: str) -> bool:
            return service in self._faults

        def get_fault(self, service: str) -> dict | None:
            return self._faults.get(service)

        def clear_all(self):
            self._faults.clear()

    injector = FaultInjector()
    yield injector
    injector.clear_all()
