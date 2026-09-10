from __future__ import annotations

import time
from collections import defaultdict
from contextlib import contextmanager
from typing import Any


class MockRedis:
    def __init__(self) -> None:
        self._data: dict[str, str | bytes] = {}
        self._expiry: dict[str, float] = {}
        self._pubsub_channels: dict[str, list[str]] = defaultdict(list)
        self._pubsub_messages: list[dict[str, Any]] = []
        self._call_history: list[dict[str, Any]] = []
        self._pipeline_commands: list[tuple[str, list[Any]]] = []

    def _check_expiry(self, key: str) -> None:
        if key in self._expiry and time.time() > self._expiry[key]:
            del self._data[key]
            del self._expiry[key]

    def _record(self, method: str, *args: Any, **kwargs: Any) -> None:
        self._call_history.append({"method": method, "args": args, "kwargs": kwargs})

    def get(self, key: str) -> str | None:
        self._record("get", key)
        self._check_expiry(key)
        val = self._data.get(key)
        if val is not None:
            if isinstance(val, bytes):
                return val.decode("utf-8")
            return str(val)
        return None

    def set(self, key: str, value: str | bytes, ex: int | None = None) -> bool:
        self._record("set", key, value, ex=ex)
        self._data[key] = value
        if ex is not None:
            self._expiry[key] = time.time() + ex
        return True

    def delete(self, key: str) -> int:
        self._record("delete", key)
        if key in self._data:
            del self._data[key]
            self._expiry.pop(key, None)
            return 1
        return 0

    def exists(self, key: str) -> bool:
        self._record("exists", key)
        self._check_expiry(key)
        return key in self._data

    def expire(self, key: str, time_sec: int) -> bool:
        self._record("expire", key, time_sec)
        if key in self._data:
            self._expiry[key] = time.time() + time_sec
            return True
        return False

    def publish(self, channel: str, message: str) -> int:
        self._record("publish", channel, message)
        self._pubsub_messages.append({"channel": channel, "message": message, "type": "message"})
        subscribers = len(self._pubsub_channels.get(channel, []))
        return subscribers

    def subscribe(self, channel: str) -> None:
        self._record("subscribe", channel)

    def get_message(self) -> dict[str, Any] | None:
        self._record("get_message")
        if self._pubsub_messages:
            return self._pubsub_messages.pop(0)
        return None

    def keys(self, pattern: str = "*") -> list[str]:
        self._record("keys", pattern)
        import fnmatch
        return [k for k in self._data if fnmatch.fnmatch(k, pattern)]

    def flushall(self) -> bool:
        self._record("flushall")
        self._data.clear()
        self._expiry.clear()
        self._pubsub_messages.clear()
        return True

    def ping(self) -> bool:
        self._record("ping")
        return True

    def setnx(self, key: str, value: str | bytes) -> bool:
        self._record("setnx", key, value)
        if key not in self._data:
            self._data[key] = value
            return True
        return False

    def lpush(self, key: str, value: str | bytes) -> int:
        self._record("lpush", key, value)
        if key not in self._data:
            self._data[key] = []
        if not isinstance(self._data[key], list):
            self._data[key] = []
        self._data[key].insert(0, value)
        return len(self._data[key])

    def rpush(self, key: str, value: str | bytes) -> int:
        self._record("rpush", key, value)
        if key not in self._data:
            self._data[key] = []
        if not isinstance(self._data[key], list):
            self._data[key] = []
        self._data[key].append(value)
        return len(self._data[key])

    def lpop(self, key: str) -> str | bytes | None:
        self._record("lpop", key)
        if key not in self._data or not isinstance(self._data[key], list) or len(self._data[key]) == 0:
            return None
        return self._data[key].pop(0)

    def rpop(self, key: str) -> str | bytes | None:
        self._record("rpop", key)
        if key not in self._data or not isinstance(self._data[key], list) or len(self._data[key]) == 0:
            return None
        return self._data[key].pop()

    def llen(self, key: str) -> int:
        self._record("llen", key)
        if key not in self._data or not isinstance(self._data[key], list):
            return 0
        return len(self._data[key])

    def lrange(self, key: str, start: int, stop: int) -> list[str | bytes]:
        self._record("lrange", key, start, stop)
        if key not in self._data or not isinstance(self._data[key], list):
            return []
        length = len(self._data[key])
        if stop >= 0:
            return list(self._data[key][start:stop + 1])
        return list(self._data[key][start:stop])

    def hset(self, key: str, field: str, value: str | bytes) -> int:
        self._record("hset", key, field, value)
        if key not in self._data:
            self._data[key] = {}
        if not isinstance(self._data[key], dict):
            self._data[key] = {}
        self._data[key][field] = value
        return 1

    def hget(self, key: str, field: str) -> str | bytes | None:
        self._record("hget", key, field)
        if key not in self._data or not isinstance(self._data[key], dict):
            return None
        val = self._data[key].get(field)
        if val is not None and isinstance(val, bytes):
            return val.decode("utf-8")
        if val is not None:
            return str(val)
        return None

    def hgetall(self, key: str) -> dict[str, str | bytes]:
        self._record("hgetall", key)
        if key not in self._data or not isinstance(self._data[key], dict):
            return {}
        result: dict[str, str | bytes] = {}
        for k, v in self._data[key].items():
            if isinstance(v, bytes):
                result[str(k)] = v.decode("utf-8")
            else:
                result[str(k)] = str(v)
        return result

    def hdel(self, key: str, field: str) -> int:
        self._record("hdel", key, field)
        if key not in self._data or not isinstance(self._data[key], dict):
            return 0
        if field in self._data[key]:
            del self._data[key][field]
            return 1
        return 0

    def incr(self, key: str) -> int:
        self._record("incr", key)
        current = self._data.get(key, 0)
        try:
            val = int(str(current)) + 1
        except (ValueError, TypeError):
            val = 1
        self._data[key] = str(val)
        return val

    def ttl(self, key: str) -> int:
        self._record("ttl", key)
        self._check_expiry(key)
        if key not in self._data:
            return -2
        if key not in self._expiry:
            return -1
        remaining = int(self._expiry[key] - time.time())
        return max(0, remaining)

    def pipeline(self) -> MockRedisPipeline:
        self._record("pipeline")
        return MockRedisPipeline(self)


class MockRedisPipeline:
    def __init__(self, redis: MockRedis) -> None:
        self._redis = redis
        self._commands: list[tuple[str, list[Any], dict[str, Any]]] = []
        self._results: list[Any] = []

    def __enter__(self) -> MockRedisPipeline:
        return self

    def __exit__(self, *args: Any) -> None:
        self.execute()

    def get(self, key: str) -> MockRedisPipeline:
        self._commands.append(("get", [key], {}))
        return self

    def set(self, key: str, value: str | bytes, ex: int | None = None) -> MockRedisPipeline:
        kwargs = {}
        if ex is not None:
            kwargs["ex"] = ex
        self._commands.append(("set", [key, value], kwargs))
        return self

    def delete(self, key: str) -> MockRedisPipeline:
        self._commands.append(("delete", [key], {}))
        return self

    def exists(self, key: str) -> MockRedisPipeline:
        self._commands.append(("exists", [key], {}))
        return self

    def execute(self) -> list[Any]:
        results = []
        for method, args, kwargs in self._commands:
            fn = getattr(self._redis, method)
            results.append(fn(*args, **kwargs))
        self._commands.clear()
        return results
