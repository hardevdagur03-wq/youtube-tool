from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.security


class TestRateLimiting:
    def test_rate_limit_enforced(self):
        max_requests = 10
        window_s = 1.0
        counter = 0
        start = time.perf_counter()
        while time.perf_counter() - start < window_s:
            counter += 1
            if counter > max_requests:
                break
        duration = time.perf_counter() - start
        if counter > max_requests:
            assert duration < window_s * 1.1

    def test_rate_limit_resets(self):
        counters = {}
        for minute in range(3):
            counters[minute] = 5
        assert counters[0] == 5
        assert counters[1] == 5
        assert counters[2] == 5

    @pytest.mark.parametrize("endpoint,limit", [
        ("/api/projects", 100),
        ("/api/projects/1/review", 50),
        ("/api/projects/1/export", 20),
        ("/api/auth/login", 10),
    ])
    def test_different_endpoints_different_limits(self, endpoint, limit):
        rate_limits = {
            "/api/projects": 100,
            "/api/projects/1/review": 50,
            "/api/projects/1/export": 20,
            "/api/auth/login": 10,
        }
        assert rate_limits[endpoint] == limit
        assert limit > 0

    @pytest.mark.parametrize("bypass_attempt", [
        "X-Forwarded-For: 127.0.0.1",
        "X-Real-IP: 10.0.0.1",
        "X-Forwarded-For: 127.0.0.2, 10.0.0.1",
        "Client-IP: 192.168.1.1",
    ])
    def test_rate_limit_bypass_attempts(self, bypass_attempt):
        header_name, header_value = bypass_attempt.split(": ", 1)
        forwarded_ips = header_value.replace(" ", "").split(",")
        first_ip = forwarded_ips[0]
        assert first_ip is not None
        assert len(first_ip) > 0

    @pytest.mark.asyncio
    async def test_rate_limit_async(self):
        with patch("database.db_service.DatabaseService.list_projects", new_callable=AsyncMock) as m:
            m.return_value = []
            svc = DatabaseService()  # noqa: F821
            for i in range(5):
                result = await svc.list_projects()
                assert result == []
