from __future__ import annotations

import logging
from typing import Any

from observability.config import ObservabilityConfig
from observability.logger import configure_logging, get_logger
from observability.tracing import TracingManager
from observability.metrics import MetricsManager


class TelemetryOrchestrator:
    def __init__(self, config: ObservabilityConfig | None = None):
        self._config = config or ObservabilityConfig.from_env()
        self.tracing = TracingManager(self._config)
        self.metrics = MetricsManager(self._config)
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        configure_logging(self._config)
        self.tracing.initialize()
        self.metrics.initialize()
        self._setup_sentry()
        self._initialized = True
        logger = get_logger(__name__)
        logger.info(
            "observability_initialized",
            config=self._config.to_dict(),
        )

    def shutdown(self) -> None:
        self.tracing.shutdown()

    def get_logger(self, name: str):
        return get_logger(name)

    def _setup_sentry(self) -> None:
        if not self._config.sentry_enabled or not self._config.sentry_dsn:
            return
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=self._config.sentry_dsn,
                sample_rate=self._config.sentry_sample_rate,
                environment=self._config.environment,
                traces_sample_rate=self._config.tracing_sample_rate,
            )
        except ImportError:
            logging.getLogger(__name__).warning("sentry_sdk not installed; skipping Sentry setup")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Sentry setup failed: {e}")


_orchestrator: TelemetryOrchestrator | None = None


def get_telemetry() -> TelemetryOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = TelemetryOrchestrator()
        _orchestrator.initialize()
    return _orchestrator
