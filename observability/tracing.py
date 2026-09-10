from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Callable, Generator
from uuid import uuid4

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SpanExporter
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio

from observability.config import ObservabilityConfig

try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    _HAS_OTLP = True
except ImportError:
    _HAS_OTLP = False
    OTLPSpanExporter = None  # type: ignore[assignment]


class TracingManager:
    def __init__(self, config: ObservabilityConfig):
        self._config = config
        self._provider: TracerProvider | None = None
        self._tracer = trace.NoOpTracer()
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized or not self._config.tracing_enabled:
            return
        resource = Resource.create({
            "service.name": self._config.service_name,
            "service.version": self._config.service_version,
            "deployment.environment": self._config.environment,
        })
        sampler = ParentBasedTraceIdRatio(self._config.tracing_sample_rate)
        self._provider = TracerProvider(resource=resource, sampler=sampler)
        if self._config.tracing_exporter == "otlp" and _HAS_OTLP and OTLPSpanExporter is not None:
            exporter = OTLPSpanExporter(endpoint=self._config.tracing_endpoint)
        elif self._config.tracing_exporter != "none":
            try:
                exporter = ConsoleSpanExporter()
            except Exception:
                exporter = None
        else:
            exporter = None
        if exporter is not None:
            self._provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(self._provider)
        self._tracer = trace.get_tracer(self._config.service_name, self._config.service_version)
        self._initialized = True

    def shutdown(self) -> None:
        if self._provider:
            self._provider.shutdown()

    def get_tracer(self):
        return self._tracer

    def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> Any:
        return self._tracer.start_as_current_span(name, attributes=attributes)

    @contextmanager
    def span(self, name: str, **attributes: Any) -> Generator[Any, None, None]:
        with self._tracer.start_as_current_span(name) as span:
            for k, v in attributes.items():
                span.set_attribute(k, str(v))
            yield span

    def inject_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            ctx = span.get_span_context()
            headers["traceparent"] = f"00-{format(ctx.trace_id, '032x')}-{format(ctx.span_id, '016x')}-{format(ctx.trace_flags, '02x')}"
        return headers


def generate_trace_id() -> str:
    return str(uuid4())


def generate_span_id() -> str:
    return str(uuid4())
