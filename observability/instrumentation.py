from __future__ import annotations

import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Generator, TypeVar
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from observability.logger import get_logger
from observability.metrics import MetricsManager
from observability.tracing import TracingManager, generate_trace_id, generate_span_id

F = TypeVar("F", bound=Callable[..., Any])


class InstrumentationContext:
    def __init__(self, metrics: MetricsManager | None = None, tracing: TracingManager | None = None):
        self.metrics = metrics
        self.tracing = tracing
        self._request_id: str | None = None
        self._context: dict[str, Any] = {}

    @property
    def request_id(self) -> str:
        if self._request_id is None:
            self._request_id = generate_trace_id()
        return self._request_id

    def set(self, key: str, value: Any) -> None:
        self._context[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._context.get(key, default)

    def get_all(self) -> dict[str, Any]:
        return dict(self._context)


class InstrumentationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, metrics: MetricsManager, tracing: TracingManager):
        super().__init__(app)
        self._metrics = metrics
        self._tracing = tracing
        self._logger = get_logger(__name__)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", generate_trace_id())
        path = request.url.path
        method = request.method
        start = time.monotonic()
        self._metrics.inc("http_requests_total", method=method, path=path)
        tracer = self._tracing.get_tracer()
        with tracer.start_as_current_span(f"{method} {path}") as span:
            span.set_attribute("http.method", method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.request_id", request_id)
            try:
                response = await call_next(request)
                duration = time.monotonic() - start
                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("http.duration_ms", duration * 1000)
                self._metrics.observe("http_request_duration_seconds", duration, method=method, path=path)
                if response.status_code >= 500:
                    self._metrics.inc("http_errors_total", method=method, path=path, status=str(response.status_code))
                response.headers["X-Request-ID"] = request_id
                return response
            except Exception as exc:
                duration = time.monotonic() - start
                span.set_attribute("http.error", str(exc))
                span.set_attribute("http.duration_ms", duration * 1000)
                self._metrics.inc("http_errors_total", method=method, path=path, status="500")
                raise


def instrument_fastapi(app: Any, metrics: MetricsManager, tracing: TracingManager) -> None:
    app.add_middleware(InstrumentationMiddleware, metrics=metrics, tracing=tracing)
    logger = get_logger(__name__)
    logger.info("fastapi_instrumentation_installed")


def instrument_function(name: str, metrics: MetricsManager | None = None, tracing: TracingManager | None = None) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.monotonic()
            if metrics:
                metrics.inc(f"func_{name}_calls_total")
            if tracing:
                tracer = tracing.get_tracer()
                with tracer.start_as_current_span(f"func_{name}") as span:
                    try:
                        result = func(*args, **kwargs)
                        if metrics:
                            metrics.observe(f"func_{name}_duration_seconds", time.monotonic() - start)
                        return result
                    except Exception as exc:
                        if metrics:
                            metrics.inc(f"func_{name}_errors_total")
                        if tracing:
                            span.set_attribute("error", str(exc))
                        raise
            else:
                try:
                    return func(*args, **kwargs)
                finally:
                    if metrics:
                        metrics.observe(f"func_{name}_duration_seconds", time.monotonic() - start)
        return wrapper
    return decorator


def instrument_method(name: str) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            metrics = getattr(self, "_metrics", None) or getattr(self, "metrics", None)
            tracing = getattr(self, "_tracing", None) or getattr(self, "tracing", None)
            start = time.monotonic()
            if metrics:
                metrics.inc(f"method_{name}_calls_total")
            if tracing:
                tracer = tracing.get_tracer()
                with tracer.start_as_current_span(f"method_{name}"):
                    try:
                        return func(self, *args, **kwargs)
                    finally:
                        if metrics:
                            metrics.observe(f"method_{name}_duration_seconds", time.monotonic() - start)
            else:
                try:
                    return func(self, *args, **kwargs)
                finally:
                    if metrics:
                        metrics.observe(f"method_{name}_duration_seconds", time.monotonic() - start)
        return wrapper
    return decorator


@contextmanager
def instrument_context(operation: str, metrics: MetricsManager | None = None, tracing: TracingManager | None = None, **attributes: Any) -> Generator[None, None, None]:
    span = None
    start = time.monotonic()
    if metrics:
        metrics.inc(f"ctx_{operation}_total")
    if tracing:
        tracer = tracing.get_tracer()
        span = tracer.start_as_current_span(f"ctx_{operation}")
        ctx = span.__enter__()
        for k, v in attributes.items():
            ctx.set_attribute(k, str(v))
    try:
        yield
    except Exception:
        if metrics:
            metrics.inc(f"ctx_{operation}_errors_total")
        raise
    finally:
        if metrics:
            metrics.observe(f"ctx_{operation}_duration_seconds", time.monotonic() - start)
        if span:
            span.__exit__(None, None, None)
