"""Production Monitoring Configuration — all settings environment-driven."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default


def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key, "").lower().strip()
    if not val:
        return default
    return val in ("1", "true", "yes", "y")


@dataclass
class ProductionMonitoringConfig:
    """Configuration for Production Monitoring & Observability — all env-driven."""

    # Loki
    loki_push_url: str = _env("MON_LOKI_PUSH_URL", "http://localhost:3100/loki/api/v1/push")
    loki_enabled: bool = _env_bool("MON_LOKI_ENABLED", True)
    loki_batch_size: int = _env_int("MON_LOKI_BATCH_SIZE", 100)
    loki_flush_interval: int = _env_int("MON_LOKI_FLUSH_INTERVAL", 5)

    # Jaeger / Tracing
    jaeger_enabled: bool = _env_bool("MON_JAEGER_ENABLED", True)
    jaeger_endpoint: str = _env("MON_JAEGER_ENDPOINT", "http://localhost:14250")
    jaeger_sampling_rate: float = float(_env("MON_JAEGER_SAMPLING_RATE", "0.1"))

    # Sentry
    sentry_dsn: str = _env("MON_SENTRY_DSN", "")
    sentry_enabled: bool = _env_bool("MON_SENTRY_ENABLED", True)
    sentry_traces_sample_rate: float = float(_env("MON_SENTRY_TRACES_RATE", "0.1"))

    # Metrics
    metrics_prefix: str = _env("MON_METRICS_PREFIX", "yt_blog")
    metrics_enabled: bool = _env_bool("MON_METRICS_ENABLED", True)

    # Alerting
    alert_slack_webhook: str = _env("MON_ALERT_SLACK_WEBHOOK", "")
    alert_email_to: str = _env("MON_ALERT_EMAIL_TO", "")
    alert_email_from: str = _env("MON_ALERT_EMAIL_FROM", "alerts@ytblog.com")

    # Health
    health_uptime_start: float = 0.0

    @classmethod
    def from_env(cls) -> ProductionMonitoringConfig:
        return cls()
