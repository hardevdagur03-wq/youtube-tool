from __future__ import annotations

import json
import logging

import pytest

from observability.logger import StructuredLogger, configure_logging, get_logger
from observability.config import ObservabilityConfig


class TestStructuredLogger:
    def test_basic_logging(self, caplog):
        caplog.set_level(logging.INFO)
        config = ObservabilityConfig(logging_level="INFO", logging_format="console")
        configure_logging(config)
        logger = get_logger("test")
        logger.info("hello world")
        assert "hello world" in caplog.text

    def test_bind_context(self):
        config = ObservabilityConfig()
        configure_logging(config)
        logger = get_logger("test_bind")
        bound = logger.bind(trace_id="abc123", request_id="req-1")
        assert bound._context["trace_id"] == "abc123"
        assert bound._context["request_id"] == "req-1"

    def test_level_methods(self):
        config = ObservabilityConfig()
        configure_logging(config)
        logger = get_logger("test_levels")
        logger.trace("trace msg")
        logger.debug("debug msg")
        logger.info("info msg")
        logger.warning("warning msg")
        logger.error("error msg")
        logger.critical("critical msg")

    def test_exception_logging(self):
        config = ObservabilityConfig()
        configure_logging(config)
        logger = get_logger("test_exc")
        try:
            raise ValueError("test error")
        except ValueError:
            logger.exception("caught exception")

    def test_get_logger_singleton(self):
        config = ObservabilityConfig()
        configure_logging(config)
        a = get_logger("singleton_test")
        b = get_logger("singleton_test")
        assert a is b
