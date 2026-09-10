from __future__ import annotations

import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Callable

from security.security_models import RateLimitError, ThreatType


@dataclass
class RateLimitRule:
    key_prefix: str
    max_requests: int
    window_seconds: int
    burst_multiplier: float = 1.0


class SecurityRateLimiter:
    def __init__(self):
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()
        self._rules: list[RateLimitRule] = []
        self._init_default_rules()

    def _init_default_rules(self) -> None:
        self._rules = [
            RateLimitRule(key_prefix="auth:", max_requests=10, window_seconds=60),
            RateLimitRule(key_prefix="api:", max_requests=60, window_seconds=60),
            RateLimitRule(key_prefix="export:", max_requests=10, window_seconds=60),
            RateLimitRule(key_prefix="ai:", max_requests=20, window_seconds=60),
            RateLimitRule(key_prefix="admin:", max_requests=100, window_seconds=60),
            RateLimitRule(key_prefix="upload:", max_requests=5, window_seconds=60),
        ]

    def add_rule(self, rule: RateLimitRule) -> None:
        self._rules.append(rule)

    def _get_rule(self, key: str) -> RateLimitRule | None:
        for rule in self._rules:
            if key.startswith(rule.key_prefix):
                return rule
        return RateLimitRule(key_prefix="default:", max_requests=30, window_seconds=60)

    def allow(self, key: str) -> bool:
        rule = self._get_rule(key)
        if rule is None:
            return True
        now = time.time()
        with self._lock:
            window = self._buckets[key]
            cutoff = now - rule.window_seconds
            window[:] = [t for t in window if t > cutoff]
            max_allowed = int(rule.max_requests * rule.burst_multiplier)
            if len(window) >= max_allowed:
                return False
            window.append(now)
            return True

    def check(self, key: str) -> None:
        if not self.allow(key):
            raise RateLimitError(f"Rate limit exceeded for {key}")

    def remaining(self, key: str) -> int:
        rule = self._get_rule(key)
        if rule is None:
            return 0
        now = time.time()
        with self._lock:
            window = self._buckets[key]
            cutoff = now - rule.window_seconds
            window[:] = [t for t in window if t > cutoff]
            max_allowed = int(rule.max_requests * rule.burst_multiplier)
            return max(0, max_allowed - len(window))

    def reset(self, key: str) -> None:
        with self._lock:
            self._buckets[key].clear()
