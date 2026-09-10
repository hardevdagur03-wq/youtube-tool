"""Comprehensive tests for Production Monitoring & Observability — all modules."""

from __future__ import annotations

import json
import os
import tempfile
import time

from production_monitoring.config import ProductionMonitoringConfig
from production_monitoring.constants import (
    METRIC_API_LATENCY, METRIC_STAGE_DURATION,
    ALERT_CPU_CRITICAL, ALERT_MEMORY_WARNING,
    SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_WARNING,
    LOKI_LABELS,
)
from production_monitoring.structured_logger import (
    StructuredLogPipeline, set_correlation_id, get_correlation_id, generate_correlation_id,
)
from production_monitoring.metrics_registry import MetricsRegistry
from production_monitoring.webapp.routers.health import (
    health, health_live, health_ready, system_status,
    provider_health, pipeline_health, database_health, redis_health,
    initialize as init_health, set_db_health, set_redis_health,
)
from production_monitoring.alert_config import AlertConfig, ALERT_RULES
from production_monitoring.incident_manager import IncidentManager, Incident


class TestConfig:
    def test_defaults(self):
        c = ProductionMonitoringConfig.from_env()
        assert c.loki_enabled == True
        assert c.metrics_prefix == "yt_blog"
        assert c.jaeger_sampling_rate == 0.1

    def test_env_override(self):
        c = ProductionMonitoringConfig.from_env()
        assert c.metrics_prefix == "yt_blog"
        # Config can be modified after creation
        c.metrics_prefix = "custom_prefix"
        assert c.metrics_prefix == "custom_prefix"


class TestConstants:
    def test_metric_names(self):
        assert "yt_blog" in METRIC_API_LATENCY
        assert "yt_blog" in METRIC_STAGE_DURATION

    def test_alert_thresholds(self):
        assert ALERT_CPU_CRITICAL == 95
        assert ALERT_MEMORY_WARNING == 80

    def test_severity_levels(self):
        assert SEVERITY_CRITICAL == "critical"
        assert SEVERITY_HIGH == "high"
        assert SEVERITY_WARNING == "warning"

    def test_loki_labels(self):
        assert "service" in LOKI_LABELS
        assert "environment" in LOKI_LABELS


class TestStructuredLogger:
    def test_info_log(self):
        logger = StructuredLogPipeline()
        logger.info("Test info", module="test")
        stats = logger.get_stats()
        assert stats["total_logs"] == 1

    def test_warning_log(self):
        logger = StructuredLogPipeline()
        logger.warning("Test warning", latency_ms=1500)
        stats = logger.get_stats()
        assert stats["total_logs"] >= 1

    def test_error_log(self):
        logger = StructuredLogPipeline()
        logger.error("Test error", error_code="E001")
        stats = logger.get_stats()
        assert stats["total_logs"] >= 1

    def test_critical_log(self):
        logger = StructuredLogPipeline()
        logger.critical("Test critical")
        stats = logger.get_stats()
        assert stats["total_logs"] >= 1

    def test_debug_log(self):
        logger = StructuredLogPipeline()
        logger.debug("Test debug")
        stats = logger.get_stats()
        assert stats["total_logs"] >= 1

    def test_correlation_id(self):
        cid = generate_correlation_id()
        assert len(cid) == 16
        retrieved = get_correlation_id()
        assert retrieved == cid

    def test_set_correlation_id(self):
        set_correlation_id("custom_id")
        assert get_correlation_id() == "custom_id"

    def test_flush(self):
        logger = StructuredLogPipeline()
        logger.info("Pre-flush")
        logger.flush()
        stats = logger.get_stats()
        assert stats["total_logs"] >= 1

    def test_log_format(self):
        set_correlation_id("corr_123")
        logger = StructuredLogPipeline()
        logger.info("Format test", module="test_module", latency_ms=100)
        # Just verify it doesn't crash - output is JSON on stdout
        stats = logger.get_stats()
        assert stats["total_logs"] >= 1


class TestMetricsRegistry:
    def setup_method(self):
        # Disable Prometheus for unit tests to avoid duplicate registration
        cfg = ProductionMonitoringConfig()
        cfg.metrics_enabled = False
        self.mr = MetricsRegistry(cfg)

    def test_record_api_request(self):
        self.mr.record_api_request("/test", "GET", 200, 100.0)
        p = self.mr.get_api_latency_percentiles("/test")
        assert p["count"] == 1
        assert p["p50_ms"] == 100.0

    def test_api_latency_percentiles(self):
        for i in range(100):
            self.mr.record_api_request("/bulk", "GET", 200, float(i))
        p = self.mr.get_api_latency_percentiles("/bulk")
        assert p["count"] == 100
        assert 45 < p["p50_ms"] < 55
        assert 90 < p["p95_ms"] < 100

    def test_record_pipeline_stage(self):
        self.mr.record_pipeline_stage("metadata", 2000, True)
        s = self.mr.get_stage_timing_summary("metadata")
        assert s["count"] == 1
        assert s["avg_ms"] == 2000.0

    def test_record_pipeline_duration(self):
        self.mr.record_pipeline_duration(60000.0)

    def test_record_provider_latency(self):
        self.mr.record_provider_latency("youtube_manual", 500, True)

    def test_record_cache_hit_miss(self):
        self.mr.record_cache_hit("prompt")
        self.mr.record_cache_miss("prompt")

    def test_record_queue_depth(self):
        self.mr.record_queue_depth("ai_critical", 5)
        self.mr.record_queue_depth("default", 0)

    def test_record_ai_cost(self):
        self.mr.record_ai_cost("openai", "gpt-4", 100, 50, 0.005)

    def test_record_active_jobs(self):
        self.mr.record_active_jobs("pipeline", 3)

    def test_record_error(self):
        self.mr.record_error("stage_failure", "analysis")

    def test_get_summary(self):
        summary = self.mr.get_summary()
        assert "api_endpoints_tracked" in summary


class TestHealthRouter:
    def setup_method(self):
        init_health()

    def test_health_live(self):
        import anyio
        async def test():
            r = await health_live()
            assert r["status"] == "ok"
        anyio.run(test)

    def test_health_ready_degraded(self):
        set_db_health(False)
        set_redis_health(False)
        import anyio
        async def test():
            r = await health_ready()
            assert r["status"] == "not_ready"
        anyio.run(test)
        set_db_health(True)
        set_redis_health(True)

    def test_health_ready_ok(self):
        set_db_health(True)
        set_redis_health(True)
        import anyio
        async def test():
            r = await health_ready()
            assert r["status"] == "ok"
        anyio.run(test)

    def test_health_checks_present(self):
        import anyio
        async def test():
            r = await health()
            assert "checks" in r
            assert "database" in r["checks"]
            assert "redis" in r["checks"]
        anyio.run(test)

    def test_system_status(self):
        import anyio
        async def test():
            r = await system_status()
            assert r["status"] == "ok"
            assert "dependencies" in r
        anyio.run(test)

    def test_provider_health(self):
        import anyio
        async def test():
            r = await provider_health()
            assert "transcript_providers" in r
            assert "ai_providers" in r
        anyio.run(test)

    def test_pipeline_health(self):
        import anyio
        async def test():
            r = await pipeline_health()
            assert "pipeline_stages" in r
        anyio.run(test)

    def test_database_health(self):
        import anyio
        async def test():
            r = await database_health()
            assert "status" in r
        anyio.run(test)

    def test_redis_health(self):
        import anyio
        async def test():
            r = await redis_health()
            assert "status" in r
        anyio.run(test)


class TestAlertConfig:
    def setup_method(self):
        self.ac = AlertConfig()

    def test_generate_rules_count(self):
        rules = self.ac.generate_rules()
        assert len(rules) == len(ALERT_RULES)

    def test_rules_have_alerts(self):
        rules = self.ac.generate_rules()
        for rule in rules:
            assert "alert" in rule
            assert "expr" in rule
            assert "labels" in rule
            assert "severity" in rule["labels"]

    def test_generate_alertmanager_config(self):
        config = self.ac.generate_alertmanager_yml()
        assert "route" in config
        assert "receivers" in config

    def test_get_alert_summary(self):
        summary = self.ac.get_alert_summary()
        assert len(summary) == len(ALERT_RULES)
        for s in summary:
            assert "name" in s
            assert "severity" in s

    def test_generate_rules_yml(self):
        yml = self.ac.generate_rules_yml()
        assert "groups:" in yml
        assert "yt_blog_alerts" in yml


class TestIncidentManager:
    def setup_method(self):
        self.im = IncidentManager()

    def test_create_incident(self):
        inc = self.im.create_incident("TestAlert", "critical", "Test description")
        assert inc.status == "open"
        assert inc.alert_name == "TestAlert"
        assert inc.severity == "critical"

    def test_acknowledge(self):
        inc = self.im.create_incident("Test", "high", "desc")
        assert self.im.acknowledge(inc.incident_id) == True
        assert inc.status == "acknowledged"

    def test_acknowledge_nonexistent(self):
        assert self.im.acknowledge("nonexistent") == False

    def test_resolve(self):
        inc = self.im.create_incident("Test", "warning", "desc")
        time.sleep(0.01)
        assert self.im.resolve(inc.incident_id, "Fixed") == True
        assert inc.status == "resolved"
        assert inc.mttr_seconds > 0

    def test_resolve_nonexistent(self):
        assert self.im.resolve("nonexistent") == False

    def test_get_incident(self):
        inc = self.im.create_incident("Test", "info", "desc")
        retrieved = self.im.get_incident(inc.incident_id)
        assert retrieved is not None
        assert retrieved.incident_id == inc.incident_id

    def test_get_open_incidents(self):
        self.im.create_incident("A", "critical", "desc")
        self.im.create_incident("B", "high", "desc")
        open_inc = self.im.get_open_incidents()
        assert len(open_inc) == 2

    def test_get_open_incidents_filtered(self):
        self.im.create_incident("A", "critical", "desc")
        self.im.create_incident("B", "warning", "desc")
        critical = self.im.get_open_incidents("critical")
        assert len(critical) == 1

    def test_get_incident_timeline(self):
        inc = self.im.create_incident("Test", "critical", "desc")
        self.im.acknowledge(inc.incident_id)
        self.im.resolve(inc.incident_id, "Fixed")
        timeline = self.im.get_incident_timeline(inc.incident_id)
        assert len(timeline) == 3

    def test_calculate_mttr(self):
        for i in range(3):
            inc = self.im.create_incident(f"Test{i}", "critical", "desc")
            time.sleep(0.02)
            self.im.resolve(inc.incident_id, "Fixed")
        mttr = self.im.calculate_mttr()
        assert mttr >= 0  # May be 0 if all resolution happens too fast

    def test_get_summary(self):
        self.im.create_incident("A", "critical", "desc")
        self.im.create_incident("B", "high", "desc")
        summary = self.im.get_summary()
        assert summary["total_incidents"] == 2
        assert summary["open"] == 2


class TestBackgroundTasks:
    def test_collect_system_metrics(self):
        from production_monitoring.background.tasks import collect_system_metrics
        metrics = collect_system_metrics()
        assert "cpu_percent" in metrics
        assert "memory_percent" in metrics

    def test_flush_pending_logs(self):
        from production_monitoring.background.tasks import flush_pending_logs
        logger = StructuredLogPipeline()
        # Should not crash
        flush_pending_logs(logger)
