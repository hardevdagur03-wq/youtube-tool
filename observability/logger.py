from __future__ import annotations

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any

from observability.config import ObservabilityConfig


_EXTRA_ATTRS = {
    "trace_id", "span_id", "request_id", "project_id", "job_id",
    "user_id", "environment", "version", "execution_time",
    "pipeline_stage", "prompt_name", "model_name", "provider",
}

_LOG_RECORD_ATTRS = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "msecs", "msg",
    "name", "pathname", "process", "processName", "relativeCreated",
    "stack_info", "thread", "threadName",
}


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        for key in _EXTRA_ATTRS:
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = "".join(traceback.format_exception(*record.exc_info))
        extra = getattr(record, "extra_data", None)
        if extra and isinstance(extra, dict):
            log_entry["extra"] = {k: v for k, v in extra.items() if not k.startswith("_")}
        return json.dumps(log_entry, default=str)


class StructuredLogger:
    def __init__(self, name: str, config: ObservabilityConfig | None = None):
        self._logger = logging.getLogger(name)
        self._config = config
        self._context: dict[str, Any] = {}

    def bind(self, **kwargs: Any) -> StructuredLogger:
        child = StructuredLogger(self._logger.name, self._config)
        child._context = {**self._context, **kwargs}
        child._logger = self._logger
        return child

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        extra: dict[str, Any] = {"extra_data": {}}
        for k, v in self._context.items():
            if k in _EXTRA_ATTRS:
                extra[k] = v
            else:
                extra["extra_data"][k] = v
        for key in list(kwargs.keys()):
            if key in _EXTRA_ATTRS:
                extra[key] = kwargs.pop(key)
            elif key not in _LOG_RECORD_ATTRS:
                extra["extra_data"][key] = kwargs[key]
        self._logger.log(level, message, extra=extra)

    def trace(self, message: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG - 5, message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("exc_info", True)
        self._log(logging.ERROR, message, **kwargs)


_loggers: dict[str, StructuredLogger] = {}
_global_config: ObservabilityConfig | None = None


def configure_logging(config: ObservabilityConfig) -> None:
    global _global_config
    _global_config = config
    root = logging.getLogger()
    root.setLevel(getattr(logging, config.logging_level, logging.INFO))
    if not root.handlers:
        handler: logging.Handler
        if config.logging_file:
            handler = logging.FileHandler(config.logging_file)
        else:
            handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        root.addHandler(handler)


def get_logger(name: str) -> StructuredLogger:
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name, _global_config)
    return _loggers[name]
