from __future__ import annotations

from observability.health_checks import (
    HealthCheckRegistry,
    HealthStatus,
    HealthCheckResult,
)


class TestHealthCheckRegistry:
    def test_register_and_run(self):
        registry = HealthCheckRegistry()
        registry.register("test", lambda: HealthCheckResult(name="test", status=HealthStatus.HEALTHY))
        result = registry.run("test")
        assert result is not None
        assert result.status == HealthStatus.HEALTHY

    def test_run_nonexistent(self):
        registry = HealthCheckRegistry()
        result = registry.run("nonexistent")
        assert result is None

    def test_unregister(self):
        registry = HealthCheckRegistry()
        registry.register("temp", lambda: HealthCheckResult(name="temp", status=HealthStatus.HEALTHY))
        registry.unregister("temp")
        assert registry.run("temp") is None

    def test_run_all(self):
        registry = HealthCheckRegistry()
        registry.register("a", lambda: HealthCheckResult(name="a", status=HealthStatus.HEALTHY))
        registry.register("b", lambda: HealthCheckResult(name="b", status=HealthStatus.DEGRADED))
        registry.register("c", lambda: HealthCheckResult(name="c", status=HealthStatus.UNHEALTHY))
        results = registry.run_all()
        assert len(results) == 3

    def test_get_summary(self):
        registry = HealthCheckRegistry()
        registry.register("ok", lambda: HealthCheckResult(name="ok", status=HealthStatus.HEALTHY))
        summary = registry.get_summary()
        assert summary["overall"] == "healthy"
        assert summary["healthy"] == 1

    def test_summary_unhealthy(self):
        registry = HealthCheckRegistry()
        registry.register("bad", lambda: HealthCheckResult(name="bad", status=HealthStatus.UNHEALTHY))
        summary = registry.get_summary()
        assert summary["overall"] == "unhealthy"

    def test_check_exception_handling(self):
        registry = HealthCheckRegistry()

        def failing_check():
            raise RuntimeError("connection failed")

        registry.register("failing", failing_check)
        result = registry.run("failing")
        assert result.status == HealthStatus.UNHEALTHY
        assert "connection failed" in result.detail

    def test_create_db_health_check(self):
        from observability.health_checks import create_database_health_check

        def mock_session_getter():
            class MockSession:
                async def execute(self, query):
                    return None
            return MockSession()

        check_fn = create_database_health_check(mock_session_getter)
        # Should not raise

    def test_create_redis_health_check(self):
        from observability.health_checks import create_redis_health_check

        def mock_redis():
            class MockRedis:
                def ping(self):
                    return True
            return MockRedis()

        check_fn = create_redis_health_check(mock_redis)
        result = check_fn()
        assert result.status == HealthStatus.HEALTHY

    def test_create_disk_health_check(self):
        from observability.health_checks import create_disk_health_check

        check_fn = create_disk_health_check(path=".")
        result = check_fn()
        assert result.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
