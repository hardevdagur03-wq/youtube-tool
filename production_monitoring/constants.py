"""Constants and metric definitions for Production Monitoring."""

from __future__ import annotations

# Metric name prefix
METRICS_PREFIX = "yt_blog"

# Standard metric names
METRIC_API_REQUEST_COUNT = f"{METRICS_PREFIX}_api_requests_total"
METRIC_API_LATENCY = f"{METRICS_PREFIX}_api_latency_ms"
METRIC_PIPELINE_DURATION = f"{METRICS_PREFIX}_pipeline_duration_ms"
METRIC_STAGE_DURATION = f"{METRICS_PREFIX}_stage_duration_ms"
METRIC_PROVIDER_LATENCY = f"{METRICS_PREFIX}_provider_latency_ms"
METRIC_CACHE_HITS = f"{METRICS_PREFIX}_cache_hits_total"
METRIC_CACHE_MISSES = f"{METRICS_PREFIX}_cache_misses_total"
METRIC_QUEUE_DEPTH = f"{METRICS_PREFIX}_queue_depth"
METRIC_AI_TOKENS = f"{METRICS_PREFIX}_ai_tokens_total"
METRIC_AI_COST = f"{METRICS_PREFIX}_ai_cost_total"
METRIC_ACTIVE_JOBS = f"{METRICS_PREFIX}_active_jobs"
METRIC_ERROR_COUNT = f"{METRICS_PREFIX}_errors_total"
METRIC_DATABASE_QUERY_TIME = f"{METRICS_PREFIX}_db_query_ms"
METRIC_REDIS_OPERATION_TIME = f"{METRICS_PREFIX}_redis_operation_ms"

# Standard label names
LABEL_SERVICE = "service"
LABEL_ENDPOINT = "endpoint"
LABEL_METHOD = "method"
LABEL_STATUS = "status"
LABEL_STAGE = "stage"
LABEL_PROVIDER = "provider"
LABEL_MODEL = "model"
LABEL_CACHE = "cache_name"
LABEL_QUEUE = "queue"
LABEL_ERROR_TYPE = "error_type"
LABEL_FORMAT = "format"

# Service names
SERVICE_API = "api"
SERVICE_WORKER = "worker"
SERVICE_BEAT = "beat"
SERVICE_FRONTEND = "frontend"
SERVICE_REDIS = "redis"
SERVICE_DATABASE = "database"

# Alert thresholds
ALERT_CPU_WARNING = 80
ALERT_CPU_CRITICAL = 95
ALERT_MEMORY_WARNING = 80
ALERT_MEMORY_CRITICAL = 95
ALERT_DISK_WARNING = 85
ALERT_DISK_CRITICAL = 95
ALERT_API_P95_WARNING_MS = 500
ALERT_API_P95_CRITICAL_MS = 2000
ALERT_CACHE_HIT_RATE_WARNING = 0.70
ALERT_CACHE_HIT_RATE_CRITICAL = 0.50
ALERT_QUEUE_DEPTH_WARNING = 100
ALERT_QUEUE_DEPTH_CRITICAL = 500
ALERT_TRANSCRIPT_FAILURE_RATE = 0.10
ALERT_PIPELINE_FAILURE_RATE = 0.05

# Severity levels
SEVERITY_CRITICAL = "critical"
SEVERITY_HIGH = "high"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"

def _get_env() -> str:
    import os
    return os.environ.get("ENVIRONMENT", "development")


# Loki log labels
LOKI_LABELS = {
    "service": "yt_blog",
    "environment": _get_env(),
}
