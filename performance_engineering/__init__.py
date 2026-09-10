"""Performance Engineering — Phase 25.

Enterprise performance optimization with async execution, parallel scheduling,
multi-level caching, batch AI processing, streaming, and comprehensive benchmarking.
"""

from __future__ import annotations

from performance_engineering.config import PerformanceConfig
from performance_engineering.connection_pool import ConnectionPoolManager
from performance_engineering.pipeline import AsyncExecutor, ParallelScheduler, BatchAIProcessor
from performance_engineering.cache import PromptCache, EmbeddingCache, QueryCache, CacheInvalidator
from performance_engineering.streaming import SSEManager, ProgressStream
from performance_engineering.queue import PriorityRouter, ThroughputOptimizer
from performance_engineering.memory import LazyLoader, MemoryOptimizer
from performance_engineering.monitoring import PerformanceDashboard, LatencyProfiler
from performance_engineering.benchmark import BenchmarkRunner, BenchmarkScenarios, BenchmarkReporter

__all__ = [
    "PerformanceConfig",
    "ConnectionPoolManager",
    "AsyncExecutor",
    "ParallelScheduler",
    "BatchAIProcessor",
    "PromptCache",
    "EmbeddingCache",
    "QueryCache",
    "CacheInvalidator",
    "SSEManager",
    "ProgressStream",
    "PriorityRouter",
    "ThroughputOptimizer",
    "LazyLoader",
    "MemoryOptimizer",
    "PerformanceDashboard",
    "LatencyProfiler",
    "BenchmarkRunner",
    "BenchmarkScenarios",
    "BenchmarkReporter",
]
