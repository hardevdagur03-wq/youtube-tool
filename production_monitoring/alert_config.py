"""Alert Configuration — AlertManager config generator and alert definitions.

Generates alertmanager.yml configuration with Slack, email, and webhook receivers.
Defines alert rules for critical, high, and warning severity levels.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from production_monitoring.config import ProductionMonitoringConfig
from production_monitoring.constants import (
    ALERT_CPU_CRITICAL,
    ALERT_MEMORY_CRITICAL,
    ALERT_DISK_CRITICAL,
    ALERT_API_P95_CRITICAL_MS,
    ALERT_CACHE_HIT_RATE_CRITICAL,
    ALERT_QUEUE_DEPTH_CRITICAL,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_WARNING,
)

logger = logging.getLogger(__name__)


# Alert rule definitions: (name, severity, expr, duration, summary)
ALERT_RULES: list[dict[str, Any]] = [
    # Critical alerts
    {
        "name": "ApplicationDown",
        "severity": SEVERITY_CRITICAL,
        "expr": "up{job='yt-blog-api'} == 0",
        "duration": "30s",
        "summary": "API application is down",
        "description": "The API service has been unreachable for 30 seconds.",
    },
    {
        "name": "DatabaseDown",
        "severity": SEVERITY_CRITICAL,
        "expr": "pg_up == 0",
        "duration": "10s",
        "summary": "PostgreSQL database is down",
        "description": "Database connection has been lost.",
    },
    {
        "name": "RedisDown",
        "severity": SEVERITY_CRITICAL,
        "expr": "redis_up == 0",
        "duration": "10s",
        "summary": "Redis is down",
        "description": "Redis cache service has been lost.",
    },
    {
        "name": "WorkerDown",
        "severity": SEVERITY_CRITICAL,
        "expr": "celery_workers_active == 0",
        "duration": "60s",
        "summary": "No active Celery workers",
        "description": "All Celery workers are unavailable for 60 seconds.",
    },
    {
        "name": "QueueOverflow",
        "severity": SEVERITY_CRITICAL,
        "expr": f"yt_blog_queue_depth > {ALERT_QUEUE_DEPTH_CRITICAL}",
        "duration": "5m",
        "summary": "Queue depth critical",
        "description": "A task queue has exceeded the critical depth threshold.",
    },
    {
        "name": "DiskFull",
        "severity": SEVERITY_CRITICAL,
        "expr": f"node_filesystem_avail_bytes / node_filesystem_size_bytes < {1 - ALERT_DISK_CRITICAL / 100}",
        "duration": "5m",
        "summary": "Disk space critically low",
        "description": "Disk usage has exceeded 95%.",
    },
    # High alerts
    {
        "name": "HighCpuUsage",
        "severity": SEVERITY_HIGH,
        "expr": f"cpu_usage_percent > {ALERT_CPU_CRITICAL}",
        "duration": "5m",
        "summary": "CPU usage critically high",
        "description": "CPU usage has exceeded 95% for 5 minutes.",
    },
    {
        "name": "HighMemoryUsage",
        "severity": SEVERITY_HIGH,
        "expr": f"memory_usage_percent > {ALERT_MEMORY_CRITICAL}",
        "duration": "5m",
        "summary": "Memory usage critically high",
        "description": "Memory usage has exceeded 95% for 5 minutes.",
    },
    {
        "name": "ApiLatencyHigh",
        "severity": SEVERITY_HIGH,
        "expr": f"yt_blog_api_latency_ms{{quantile='0.95'}} > {ALERT_API_P95_CRITICAL_MS}",
        "duration": "5m",
        "summary": "API P95 latency critical",
        "description": "API P95 latency has exceeded 2000ms for 5 minutes.",
    },
    {
        "name": "PipelineFailureRate",
        "severity": SEVERITY_HIGH,
        "expr": "rate(yt_blog_errors_total{error_type='stage_failure'}[5m]) > 0.05",
        "duration": "5m",
        "summary": "Pipeline failure rate elevated",
        "description": "Pipeline stage failure rate exceeds 5%.",
    },
    # Warning alerts
    {
        "name": "CacheHitRateLow",
        "severity": SEVERITY_WARNING,
        "expr": f"yt_blog_cache_hit_rate < {ALERT_CACHE_HIT_RATE_CRITICAL}",
        "duration": "10m",
        "summary": "Cache hit rate critically low",
        "description": "Overall cache hit rate has fallen below 50%.",
    },
    {
        "name": "TranscriptFailureRate",
        "severity": SEVERITY_WARNING,
        "expr": "rate(yt_blog_errors_total{error_type='provider_failure'}[5m]) > 0.10",
        "duration": "5m",
        "summary": "Transcript provider failure rate high",
        "description": "Transcript provider failure rate exceeds 10%.",
    },
    {
        "name": "ErrorRateIncrease",
        "severity": SEVERITY_WARNING,
        "expr": "rate(yt_blog_errors_total[5m]) > rate(yt_blog_errors_total[30m]) * 2",
        "duration": "10m",
        "summary": "Error rate increasing",
        "description": "Error rate has doubled compared to the last 30 minutes.",
    },
]


class AlertConfig:
    """Generates AlertManager configuration and alert rules.

    Usage::

        config = AlertConfig()
        rules = config.generate_rules()
        alertmanager_yml = config.generate_alertmanager_yml()
    """

    def __init__(self, config: ProductionMonitoringConfig | None = None) -> None:
        self._config = config or ProductionMonitoringConfig.from_env()

    def generate_rules(self) -> list[dict[str, Any]]:
        """Generate alert rule definitions.

        Returns:
            List of alert rule dicts compatible with Prometheus.
        """
        rules = []
        for alert in ALERT_RULES:
            rules.append({
                "alert": alert["name"],
                "expr": alert["expr"],
                "for": alert["duration"],
                "labels": {
                    "severity": alert["severity"],
                    "service": "yt_blog",
                },
                "annotations": {
                    "summary": alert["summary"],
                    "description": alert["description"],
                },
            })
        return rules

    def generate_alertmanager_yml(self) -> dict[str, Any]:
        """Generate AlertManager configuration as a dict.

        Returns:
            Dict representation of alertmanager.yml.
        """
        receivers = [
            {
                "name": "default",
                "slack_configs": [],
                "email_configs": [],
            }
        ]

        slack_webhook = self._config.alert_slack_webhook
        email_to = self._config.alert_email_to

        if slack_webhook:
            receivers.append({
                "name": "slack-critical",
                "slack_configs": [{
                    "api_url": slack_webhook,
                    "channel": "#alerts-critical",
                    "send_resolved": True,
                    "title": '{{ .GroupLabels.alertname }} [{{ .Labels.severity }}]',
                    "text": "{{ .CommonAnnotations.description }}",
                }],
            })

        if email_to:
            receivers.append({
                "name": "email-admin",
                "email_configs": [{
                    "to": email_to,
                    "from": self._config.alert_email_from,
                    "send_resolved": True,
                }],
            })

        routes = [
            {
                "receiver": "slack-critical",
                "match": {"severity": "critical"},
                "continue": True,
            },
            {
                "receiver": "email-admin",
                "match": {"severity": "critical"},
            },
            {
                "receiver": "slack-critical",
                "match": {"severity": "high"},
            },
            {
                "receiver": "default",
                "match_re": {"severity": "warning|info"},
            },
        ]

        return {
            "global": {
                "resolve_timeout": "5m",
                "smtp_smarthost": "localhost:25",
                "smtp_from": self._config.alert_email_from,
            },
            "route": {
                "receiver": "default",
                "group_by": ["alertname", "severity"],
                "group_wait": "10s",
                "group_interval": "5m",
                "repeat_interval": "4h",
                "routes": routes,
            },
            "receivers": receivers,
        }

    def get_alert_summary(self) -> list[dict[str, Any]]:
        """Get a human-readable summary of all alerts.

        Returns:
            List of alert summaries.
        """
        return [
            {
                "name": alert["name"],
                "severity": alert["severity"],
                "summary": alert["summary"],
            }
            for alert in ALERT_RULES
        ]

    def generate_rules_yml(self) -> str:
        """Generate Prometheus rules YAML content.

        Returns:
            YAML string for Prometheus rules file.
        """
        rules = self.generate_rules()
        lines = ["groups:"]
        lines.append("  - name: yt_blog_alerts")
        lines.append("    rules:")
        for rule in rules:
            lines.append(f"      - alert: {rule['alert']}")
            lines.append(f"        expr: {rule['expr']}")
            lines.append(f"        for: {rule['for']}")
            lines.append(f"        labels:")
            for k, v in rule['labels'].items():
                lines.append(f"          {k}: {v}")
            lines.append(f"        annotations:")
            for k, v in rule['annotations'].items():
                lines.append(f"          {k}: \"{v}\"")
        return "\n".join(lines)
