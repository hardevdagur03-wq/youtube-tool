"""Pipeline Hardening Configuration — all settings driven by environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default


def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key, "").lower().strip()
    if not val:
        return default
    return val in ("1", "true", "yes", "y")


def _env_list(key: str, default: str) -> list[str]:
    val = os.environ.get(key, default)
    return [v.strip() for v in val.split(",") if v.strip()]


@dataclass
class PipelineHardeningConfig:
    """Configuration for Production Pipeline Hardening.

    All values are environment-driven with sensible defaults.
    """

    # Per-stage timeouts (seconds)
    timeout_metadata: int = _env_int("PIPELINE_TIMEOUT_METADATA", 15)
    timeout_transcript: int = _env_int("PIPELINE_TIMEOUT_TRANSCRIPT", 60)
    timeout_analysis: int = _env_int("PIPELINE_TIMEOUT_ANALYSIS", 45)
    timeout_knowledge_graph: int = _env_int("PIPELINE_TIMEOUT_KNOWLEDGE_GRAPH", 20)
    timeout_seo: int = _env_int("PIPELINE_TIMEOUT_SEO", 20)
    timeout_outline: int = _env_int("PIPELINE_TIMEOUT_OUTLINE", 20)
    timeout_sections: int = _env_int("PIPELINE_TIMEOUT_SECTIONS", 60)
    timeout_review: int = _env_int("PIPELINE_TIMEOUT_REVIEW", 20)
    timeout_export: int = _env_int("PIPELINE_TIMEOUT_EXPORT", 20)
    timeout_publishing: int = _env_int("PIPELINE_TIMEOUT_PUBLISHING", 30)

    # Checkpoint configuration
    checkpoint_db_enabled: bool = _env_bool("PIPELINE_CHECKPOINT_DB_ENABLED", True)
    checkpoint_retention_days: int = _env_int("PIPELINE_CHECKPOINT_RETENTION_DAYS", 30)

    # Snapshot configuration
    snapshot_enabled: bool = _env_bool("PIPELINE_SNAPSHOT_ENABLED", True)
    snapshot_retention_count: int = _env_int("PIPELINE_SNAPSHOT_RETENTION_COUNT", 50)

    # Idempotency
    idempotency_key_ttl_days: int = _env_int("PIPELINE_IDEMPOTENCY_KEY_TTL_DAYS", 7)

    # Transaction log
    transaction_log_enabled: bool = _env_bool("PIPELINE_TX_LOG_ENABLED", True)
    transaction_log_retention_days: int = _env_int("PIPELINE_TX_LOG_RETENTION_DAYS", 90)

    # DLQ
    dlq_enabled: bool = _env_bool("PIPELINE_DLQ_ENABLED", True)
    dlq_retention_days: int = _env_int("PIPELINE_DLQ_RETENTION_DAYS", 30)

    # Retry configuration
    retry_ai_max_retries: int = _env_int("PIPELINE_RETRY_AI_MAX", 3)
    retry_database_max_retries: int = _env_int("PIPELINE_RETRY_DATABASE_MAX", 2)
    retry_network_max_retries: int = _env_int("PIPELINE_RETRY_NETWORK_MAX", 3)
    retry_base_delay: float = _env_float("PIPELINE_RETRY_BASE_DELAY", 1.0)
    retry_max_delay: float = _env_float("PIPELINE_RETRY_MAX_DELAY", 60.0)

    # Recovery
    recovery_scan_interval: int = _env_int("PIPELINE_RECOVERY_SCAN_INTERVAL", 30)
    recovery_max_attempts: int = _env_int("PIPELINE_RECOVERY_MAX_ATTEMPTS", 3)

    @classmethod
    def from_env(cls) -> PipelineHardeningConfig:
        return cls()

    def get_timeout(self, stage: str) -> int:
        """Get the timeout for a specific stage."""
        mapping = {
            "metadata": self.timeout_metadata,
            "transcript": self.timeout_transcript,
            "analysis": self.timeout_analysis,
            "knowledge_graph": self.timeout_knowledge_graph,
            "seo": self.timeout_seo,
            "outline": self.timeout_outline,
            "sections": self.timeout_sections,
            "review": self.timeout_review,
            "export": self.timeout_export,
            "publishing": self.timeout_publishing,
        }
        return mapping.get(stage, 30)
