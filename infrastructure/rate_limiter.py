from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

MAX_WINDOW_ENTRIES = 10000


class SlidingWindowRateLimiter:
    """Sliding window rate limiter per key with bounded memory."""

    def __init__(self, max_requests: int = 60, window_seconds: float = 60.0) -> None:
        self._max_requests = max_requests
        self._window = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def allow(self, key: str = "default") -> bool:
        now = time.time()
        cutoff = now - self._window
        with self._lock:
            timestamps = self._buckets[key]
            timestamps[:] = [t for t in timestamps if t > cutoff]
            if len(timestamps) >= self._max_requests:
                return False
            timestamps.append(now)
            if len(timestamps) > MAX_WINDOW_ENTRIES:
                timestamps[:] = timestamps[-self._max_requests:]
            return True

    def remaining(self, key: str = "default") -> int:
        now = time.time()
        cutoff = now - self._window
        with self._lock:
            timestamps = self._buckets[key]
            timestamps[:] = [t for t in timestamps if t > cutoff]
            return max(0, self._max_requests - len(timestamps))

    def reset(self, key: str = "default") -> None:
        with self._lock:
            self._buckets[key] = []


class YouTubeQuotaTracker:
    """Tracks YouTube API quota usage with bounded memory."""

    def __init__(self, daily_quota: int = 10000) -> None:
        self._daily_quota = daily_quota
        self._costs: list[tuple[float, int]] = []
        self._lock = Lock()

    @property
    def daily_quota(self) -> int:
        return self._daily_quota

    @daily_quota.setter
    def daily_quota(self, value: int) -> None:
        self._daily_quota = value

    def record_call(self, cost: int = 1) -> bool:
        now = time.time()
        day_ago = now - 86400
        with self._lock:
            self._costs[:] = [(t, c) for t, c in self._costs if t > day_ago]
            total = sum(c for _, c in self._costs)
            if total + cost > self._daily_quota:
                return False
            self._costs.append((now, cost))
            if len(self._costs) > MAX_WINDOW_ENTRIES:
                self._costs[:] = self._costs[-MAX_WINDOW_ENTRIES:]
            return True

    def usage(self) -> dict:
        now = time.time()
        day_ago = now - 86400
        with self._lock:
            self._costs[:] = [(t, c) for t, c in self._costs if t > day_ago]
            total = sum(c for _, c in self._costs)
            return {
                "used": total,
                "limit": self._daily_quota,
                "remaining": max(0, self._daily_quota - total),
                "percent": round((total / self._daily_quota) * 100, 1) if self._daily_quota > 0 else 0,
            }


quota_tracker = YouTubeQuotaTracker()
rate_limiter = SlidingWindowRateLimiter()
