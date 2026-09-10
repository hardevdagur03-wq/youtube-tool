"""Performance targets and threshold constants."""

from __future__ import annotations

# Performance targets (P95, in milliseconds)
PERFORMANCE_TARGETS = {
    "metadata_p95_ms": 2000,
    "transcript_p95_ms": 15000,
    "analysis_p95_ms": 15000,
    "knowledge_graph_p95_ms": 10000,
    "seo_p95_ms": 10000,
    "outline_p95_ms": 10000,
    "sections_p95_ms": 20000,
    "review_p95_ms": 10000,
    "export_p95_ms": 5000,
    "api_p95_ms": 300,
    "dashboard_p95_ms": 2000,
}

# Cache targets
CACHE_TARGET_HIT_RATE = 0.90
CACHE_TARGET_LOOKUP_MS = 5
CACHE_TARGET_STORE_MS = 10

# throughput targets
THROUGHPUT_TARGET_MULTIPLIER = 3.0

# Resource thresholds
CPU_MAX_PERCENT = 70
MEMORY_MAX_PERCENT = 75
MEMORY_MAX_HEAP_MB = 500
GC_MAX_TIME_MS = 100
CONNECTION_POOL_MAX_USAGE = 0.80
QUEUE_MAX_DEPTH = 1000

# Alert thresholds
ALERT_LATENCY_P95_WARNING_MS = 2000
ALERT_LATENCY_P95_CRITICAL_MS = 5000
ALERT_CACHE_HIT_RATE_WARNING = 0.70
ALERT_CACHE_HIT_RATE_CRITICAL = 0.50
ALERT_CPU_WARNING = 80
ALERT_CPU_CRITICAL = 95
ALERT_MEMORY_WARNING = 80
ALERT_MEMORY_CRITICAL = 95

# Profiling
PROFILE_ENABLED = True
PROFILE_SLOW_THRESHOLD_MS = 1000
PROFILE_FLAMEGRAPH_ENABLED = True

# Batch AI
BATCH_AI_MAX_TOKENS = 4000
BATCH_AI_TIMEOUT_SECONDS = 30

# Streaming
STREAMING_CHUNK_SIZE = 1024
STREAMING_SSE_RETRY_INTERVAL = 3000  # ms

# Async executor
ASYNC_DEFAULT_TIMEOUT_SECONDS = 60
ASYNC_MAX_WORKERS = 8
